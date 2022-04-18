package main

import (
	"bufio"
	"fmt"
	"io"
	"log"
	"net"

	"github.com/fausecteam/ctf-gameserver/go/checkerlib"
)

func main() {
	checkerlib.RunCheck(checker{})
}

type checker struct{}

func (c checker) PlaceFlag(ip string, team int, tick int) (checkerlib.Result, error) {
	conn, err := connect(ip)
	if err != nil {
		return -1, err
	}
	defer conn.Close()

	flag := checkerlib.GetFlag(tick)

	_, err = fmt.Fprintf(conn, "SET %d %s\n", tick, flag)
	if err != nil {
		return -1, err
	}
	log.Printf("Sent SET command: %d %s", tick, flag)

	line, err := readLine(conn)
	if err != nil {
		return -1, err
	}
	log.Printf("Received response to SET command: %q", line)

	if line != "OK" {
		log.Print("Received wrong response to SET command")
		return checkerlib.ResultFaulty, nil
	}

	return checkerlib.ResultOk, nil
}

func (c checker) CheckService(ip string, team int) (checkerlib.Result, error) {
	conn, err := connect(ip)
	if err != nil {
		return -1, err
	}
	defer conn.Close()

	_, err = fmt.Fprint(conn, "XXX\n")
	if err != nil {
		return -1, err
	}
	log.Print("Sent dummy command")

	line, err := readLine(conn)
	if err != nil {
		return -1, err
	}
	log.Printf("Received response to SET command: %q", line)

	return checkerlib.ResultOk, nil
}

func (c checker) CheckFlag(ip string, team int, tick int) (checkerlib.Result, error) {
	conn, err := connect(ip)
	if err != nil {
		return -1, err
	}
	defer conn.Close()

	_, err = fmt.Fprintf(conn, "GET %d\n", tick)
	if err != nil {
		return -1, err
	}
	log.Printf("Sent GET command: %d", tick)

	line, err := readLine(conn)
	if err != nil {
		return -1, err
	}
	log.Printf("Received response to GET command: %q", line)

	flag := checkerlib.GetFlag(tick)
	if line != flag {
		log.Print("Received wrong response to GET command")
		return checkerlib.ResultFlagNotFound, nil
	}

	return checkerlib.ResultOk, nil
}

// Helper functions

func connect(ip string) (net.Conn, error) {
	return checkerlib.Dial("tcp", net.JoinHostPort(ip, "9999"))
}

func readLine(r io.Reader) (string, error) {
	s := bufio.NewScanner(r)
	if !s.Scan() {
		err := s.Err()
		if err == nil {
			err = io.EOF
		}
		return "", nil
	}
	return s.Text(), nil
}
