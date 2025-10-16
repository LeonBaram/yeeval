package main

import (
	"bufio"
	"fmt"
	"os"
	"strings"
	"yeeval/luaparse"

	"github.com/goccy/go-yaml"
	"github.com/goccy/go-yaml/ast"
)

var didReadStdin = false
var stdin string

func Stdin() string {
	if didReadStdin {
		return stdin
	}
	scanner := bufio.NewScanner(os.Stdin)
	lines := []string{}
	for scanner.Scan() {
		lines = append(lines, scanner.Text())
	}
	stdin = strings.Join(lines, "\n")
	didReadStdin = true
	return stdin
}

func Load(input string) (ast.Node, yaml.CommentMap, error) {
	var root ast.Node
	comments := yaml.CommentMap{}

	if err := yaml.UnmarshalWithOptions([]byte(input), &root, yaml.CommentToMap(comments)); err != nil {
		return nil, nil, fmt.Errorf("error unmarshalling yaml: %v\n", err)
	}

	return root, comments, nil
}

func Output(root ast.Node, comments yaml.CommentMap) (string, error) {
	output, err := yaml.MarshalWithOptions(root, yaml.WithComment(comments))
	if err != nil {
		return "", fmt.Errorf("error marshalling yaml: %v\n", err)
	}
	return string(output), nil
}

func main() {
	input := Stdin()

	_, comments, err := Load(input)
	if err != nil {
		panic(err)
	}

	path, err := yaml.PathString("$.a[0]")
	if err != nil {
		panic(fmt.Errorf("error getting path string: %v\n", err))
	}

	var val int
	if err := path.Read(strings.NewReader(input), &val); err != nil {
		panic(fmt.Errorf("error reading path string: %v\n", err))
	}
	// fmt.Println(val)
	//
	// fmt.Println(Output(root, comments))
	//
	// for key, val := range comments {
	// 	fmt.Printf("%s: %v\n", key, val[0].Texts[0])
	// }

	cmt := comments["$.a[2]"][0].Texts[0]
	cmt = strings.TrimPrefix(cmt, "=")

	res, err := luaparse.Eval(cmt)
	if err != nil {
		panic(err)
	}
	fmt.Println(res)
}
