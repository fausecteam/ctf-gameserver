// Communication with checkermaster

package checkerlib

import (
	"bufio"
	"bytes"
	"encoding/json"
	"io"
	"sync"
)

type ipcData struct {
	sync.Mutex

	in  *bufio.Scanner
	out io.Writer
}

func (i *ipcData) Send(action string, param interface{}) {
	ipc.Lock()
	defer ipc.Unlock()

	i.send(action, param)
}
func (i *ipcData) SendRecv(action string, param interface{}) interface{} {
	ipc.Lock()
	defer ipc.Unlock()

	i.send(action, param)
	return i.recv()
}

func (i *ipcData) send(action string, param interface{}) {
	data := struct {
		Action string      `json:"action"`
		Param  interface{} `json:"param"`
	}{
		action,
		param,
	}

	x, err := json.Marshal(data)
	if err != nil {
		panic(err)
	}
	// Make sure that our JSON consists of just a single line as required
	// by IPC protocol
	x = append(bytes.Replace(x, []byte{'\n'}, nil, -1), '\n')

	_, err = i.out.Write(x)
	if err != nil {
		panic(err)
	}
}

func (i *ipcData) recv() interface{} {
	if !i.in.Scan() {
		panic(i.in.Err())
	}
	var x struct {
		Response interface{} `json:"response"`
	}
	err := json.Unmarshal(i.in.Bytes(), &x)
	if err != nil {
		panic(err)
	}
	return x.Response
}
