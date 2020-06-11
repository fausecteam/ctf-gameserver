package checkerlib

type logger struct{}

// "log" calls Write() once per log call
func (l logger) Write(p []byte) (int, error) {
	x := struct {
		Message string `json:"message"`
		//`json:"levelno"`
		//`json:"pathname"`
		//`json:"lineno"`
		//`json:"funcName"`
	}{
		string(p),
	}
	ipc.Send("LOG", x)
	return len(p), nil
}
