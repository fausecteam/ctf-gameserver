// Checkerlib implementation for Go

package checkerlib

import (
	"bufio"
	"bytes"
	"encoding/base64"
	"encoding/binary"
	"encoding/json"
	"io/ioutil"
	"log"
	"net"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"syscall"
	"time"

	"golang.org/x/crypto/sha3"
)

const (
	Timeout        = 10 * time.Second
	localStatePath = "_state.json"
)

type Result int

// Constants from src/ctf_gameserver/lib/checkresult.py
const (
	ResultInvalid      Result = -1
	ResultOk                  = 0
	ResultDown                = 1
	ResultFaulty              = 2
	ResultFlagNotFound        = 3
	ResultRecovering          = 4
)

func (r Result) String() string {
	switch r {
	case ResultOk:
		return "OK"
	case ResultDown:
		return "DOWN"
	case ResultFaulty:
		return "FAULTY"
	case ResultFlagNotFound:
		return "FLAG_NOT_FOUND"
	case ResultRecovering:
		return "RECOVERING"
	case ResultInvalid:
		return "invalid result"
	default:
		panic("Unknown result")
	}
}

var ipc ipcData

func init() {
	// Set timeouts for package "net/http"
	http.DefaultClient.Timeout = Timeout
	http.DefaultTransport.(*http.Transport).DialContext = (&net.Dialer{
		Timeout:   Timeout,
		KeepAlive: Timeout,
		DualStack: true,
	}).DialContext

	// Local execution without a Checker Runner
	if os.Getenv("CTF_CHECKERSCRIPT") == "" {
		return
	}

	f := os.NewFile(3, "in")
	if f == nil {
		log.Fatal("cannot open fd 3")
	}
	ipc.in = bufio.NewScanner(f)

	ipc.out = os.NewFile(4, "out")
	if ipc.out == nil {
		log.Fatal("cannot open fd 4")
	}

	log.SetOutput(logger{})
	// Remove date and time from log messages as the Control Master logger
	// automatically adds them
	log.SetFlags(0)
}

// Interface for individual Checker implementations.
type Checker interface {
	PlaceFlag(ip string, team int, tick int) (Result, error)
	CheckService(ip string, team int) (Result, error)
	CheckFlag(ip string, team int, tick int) (Result, error)
}

var teamId int // for local runner only

// GetFlag may be called by Checker Scripts to get the flag for a given tick,
// for the team and service of the current run. The returned flag can be used
// for both placement and checks.
func GetFlag(tick int) string {
	if ipc.in != nil {
		x := ipc.SendRecv("FLAG", map[string]interface{}{
			"tick": tick,
		})
		return x.(string)
	}

	// Return dummy flag when launched locally
	if teamId == 0 {
		panic("GetFlag() must be called through RunCheck()")
	}
	return genFlag(tick, 42, teamId, []byte("TOPSECRET"))
}

func genFlag(timestamp, flag, team int, secret []byte) string {
	// From src/ctf_gameserver/lib/flag.py

	var b bytes.Buffer
	binary.Write(&b, binary.BigEndian, uint64(timestamp))
	binary.Write(&b, binary.BigEndian, uint32(flag))
	binary.Write(&b, binary.BigEndian, uint16(team))

	d := sha3.New256()
	d.Write(secret)
	d.Write(b.Bytes())
	mac := d.Sum(nil)

	b.Write(mac[:10])
	return "FLAG_" + base64.StdEncoding.EncodeToString(b.Bytes())
}

// SetFlagID stores the Flag ID for the current team and tick.
func SetFlagID(data string) {
	if ipc.in != nil {
		ipc.SendRecv("FLAGID", data)
		// Wait for acknowledgement, result is ignored
	} else {
		log.Printf("Storing Flag ID: %q", data)
	}
}

// StoreState allows a Checker Script to store data (serialized via
// encoding/json) persistently across runs. Data is stored per service and
// team with the given key as an additional identifier.
func StoreState(key string, data interface{}) {
	// Serialize data
	x, err := json.Marshal(data)
	if err != nil {
		panic(err)
	}
	encoded := base64.StdEncoding.EncodeToString(x)

	if ipc.in != nil {
		ipc.SendRecv("STORE", map[string]string{
			"key":  key,
			"data": encoded,
		})
		// Wait for acknowledgement, result is ignored
	} else {
		x, err := ioutil.ReadFile(localStatePath)
		if err != nil {
			if !os.IsNotExist(err) {
				panic(err)
			}
			x = []byte("{}")
		}

		var state map[string]string
		err = json.Unmarshal(x, &state)
		if err != nil {
			panic(err)
		}

		state[key] = encoded

		x, err = json.Marshal(state)
		if err != nil {
			panic(err)
		}

		err = ioutil.WriteFile(localStatePath, x, 0644)
		if err != nil {
			panic(err)
		}
	}
}

// LoadState allows to retrieve data stored through StoreState by unmarshalling it into data.
// If no data exists for the given key (and the current service and team)
// false is returned.
func LoadState(key string, data interface{}) bool {
	var dataJson string
	if ipc.in != nil {
		x := ipc.SendRecv("LOAD", key)
		if x == nil {
			return false
		}
		dataJson = x.(string)
	} else {
		x, err := ioutil.ReadFile(localStatePath)
		if err != nil {
			if os.IsNotExist(err) {
				return false
			}
			panic(err)
		}

		var state map[string]string
		err = json.Unmarshal(x, &state)
		if err != nil {
			panic(err)
		}

		var ok bool
		dataJson, ok = state[key]
		if !ok {
			return false
		}
	}

	// Deserialize data
	x, err := base64.StdEncoding.DecodeString(dataJson)
	if err != nil {
		panic(err)
	}

	err = json.Unmarshal(x, data)
	if err != nil {
		panic(err)
	}
	return true
}

// RunCheck launches the execution of the specified Checker implementation.
// Must be called by all Checker Scripts.
func RunCheck(checker Checker) {
	if len(os.Args) != 4 {
		log.Fatalf("usage: %s <ip> <team-net-no> <tick>", os.Args[0])
	}

	ip := os.Args[1]
	team, err := strconv.Atoi(os.Args[2])
	if err != nil {
		log.Fatalf("invalid team net number %s", os.Args[2])
	}
	tick, err := strconv.Atoi(os.Args[3])
	if err != nil {
		log.Fatalf("invalid tick %s", os.Args[3])
	}

	// GetFlag() only needs to know the team when launched locally
	if ipc.in == nil {
		teamId = team
	}

	res, err := runCheckSteps(checker, ip, team, tick)
	if err != nil {
		if isConnError(err) {
			log.Printf("Connection error during check: %s", err)
			res = ResultDown
		} else {
			log.Fatal(err)
		}
	}

	if ipc.in != nil {
		ipc.SendRecv("RESULT", res)
	} else {
		log.Printf("Check result: %s", res)
	}
}

func runCheckSteps(checker Checker, ip string, team int, tick int) (Result, error) {
	log.Printf("Placing flag")
	res, err := checker.PlaceFlag(ip, team, tick)
	if err != nil {
		return ResultInvalid, err
	}
	log.Printf("Flag placement result: %s", res)
	if res != ResultOk {
		return res, nil
	}

	log.Printf("Checking service")
	res, err = checker.CheckService(ip, team)
	if err != nil {
		return ResultInvalid, err
	}
	log.Printf("Service check result: %s", res)
	if res != ResultOk {
		return res, nil
	}

	const lookback = 5

	oldestTick := tick - lookback
	if oldestTick < 0 {
		oldestTick = 0
	}

	recovering := false
	for curTick := tick; curTick >= oldestTick; curTick -= 1 {
		log.Printf("Checking flag of tick %d", curTick)
		res, err = checker.CheckFlag(ip, team, curTick)
		if err != nil {
			return ResultInvalid, err
		}
		log.Printf("Flag check result of tick %d: %s", curTick, res)
		if res != ResultOk {
			if curTick != tick && res == ResultFlagNotFound {
				recovering = true
			} else {
				return res, nil
			}
		}
	}
	if recovering {
		return ResultRecovering, nil
	}
	return ResultOk, nil
}

func isConnError(err error) bool {
	// From src/ctf_gameserver/checkerlib/lib.py
	errnos := []syscall.Errno{
		syscall.EACCES,
		syscall.ECONNABORTED,
		syscall.ECONNREFUSED,
		syscall.ECONNRESET,
		syscall.EHOSTDOWN,
		syscall.EHOSTUNREACH,
		syscall.ENETDOWN,
		syscall.ENETRESET,
		syscall.ENETUNREACH,
		syscall.EPIPE,
		syscall.ETIMEDOUT,
	}

	// Returned by package "net/http"
	urlErr, ok := err.(*url.Error)
	if ok {
		if urlErr.Timeout() {
			return true
		}
		err = urlErr.Err // may be net.OpError
	}
	// Returned by package "net"
	opErr, ok := err.(*net.OpError)
	if ok {
		if opErr.Timeout() {
			return true
		}
		syscallErr, ok := opErr.Err.(*os.SyscallError)
		if ok {
			for _, x := range errnos {
				if x == syscallErr.Err {
					return true
				}
			}
		}
	}
	return false
}
