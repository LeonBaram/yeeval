package luaparse

import (
	"fmt"

	"github.com/Shopify/go-lua"
)

var l = lua.NewState()

func init() {
	lua.OpenLibraries(l)
}

func LoadFile(fileName string) error {
	return lua.DoFile(l, fileName)
}

func Eval(luaExpr string) (any, error) {
	chunk := fmt.Sprintf("return (%s)", luaExpr)
	if err := lua.DoString(l, chunk); err != nil {
		return nil, err
	}
	val, ok := luaToGo(-1)
	if !ok {
		return nil, fmt.Errorf("error reading lua value")
	}
	l.Pop(1)
	return val, nil
}

var empty = struct{}{}

func luaToGo(index int) (any, bool) {
	switch l.TypeOf(index) {
	case lua.TypeNil:
		return nil, true
	case lua.TypeBoolean:
		return l.ToBoolean(index), l.IsBoolean(index)
	case lua.TypeNumber:
		val, ok := l.ToNumber(index)
		if val == float64(int(val)) {
			return int(val), ok
		}
		return val, ok
	case lua.TypeString:
		return l.ToString(index)
	case lua.TypeTable:
		return tableToGo(index)
	default:
		return nil, false
	}
}

func tableToGo(index int) (any, bool) {
	hashmap := make(map[any]any)
	slice := []any{}

	// iterate over table using lua.State.Next()
	// (see their docs for more info)
	l.PushNil()
	for l.Next(index) {
		key, ok := luaToGo(-2)
		if !ok {
			return nil, false
		}
		val, ok := luaToGo(-1)
		if !ok {
			return nil, false
		}
		hashmap[key] = val
		if intKey, ok := key.(int); ok {
			for len(slice) <= intKey {
				slice = append(slice, empty)
			}
			slice[intKey] = val
		}
		l.Pop(1)
	}
	if len(slice) == len(hashmap) {
		validSlice := true
		for _, val := range slice {
			if val == empty {
				validSlice = false
				break
			}
		}
		if validSlice {
			return slice, true
		}
	}
	return hashmap, true
}
