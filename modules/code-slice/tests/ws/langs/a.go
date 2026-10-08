package main

func Add(a int, b int) int {
	if a > 0 {
		return a + b
	}
	return b
}

type S struct{}

func (s S) M() int {
	return Add(1, 2)
}
