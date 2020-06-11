package checkerlib

import (
	"net"
)

// Dial calls net.DialTimeout with an appropriate timeout.
func Dial(network, address string) (net.Conn, error) {
	return net.DialTimeout(network, address, Timeout)
}
