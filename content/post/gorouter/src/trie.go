package main

import (
	"net/http"
	"regexp"
	"strings"
)

type node struct {
	handlers map[string]http.Handler
	leaves   map[string]*node
	regex    map[string]*regexp.Regexp
}

func newNode() *node {
	return &node{
		handlers: map[string]http.Handler{},
		leaves:   map[string]*node{},
		regex:    map[string]*regexp.Regexp{},
	}
}

func (node *node) getLeaf(v string) (*node, []string) {
	if node, ok := node.leaves[v]; ok {
		return node, nil
	}
	for key, regex := range node.regex {
		if regex.MatchString(v) {
			return node.leaves[key], []string{key, v}
		}
	}
	return nil, nil
}

func parse(c string) (string, *regexp.Regexp) {
	if string(c[0]) == ":" {
		// Given c=":id:^[0-9]$", then pattern=[":id" "^[0-9]$"]
		pattern := strings.Split(c[1:], ":")
		if re, err := regexp.Compile(pattern[1]); err == nil {
			return pattern[0], re
		}
	}
	return c, nil
}

func (node *node) append(path []string) *node {
	if len(path) == 0 {
		return node
	}
	component, regex := parse(path[0])

	leaf, _ := node.getLeaf(component)
	if leaf == nil {
		node.leaves[component] = newNode()
		leaf = node.leaves[component]

		if regex != nil {
			node.regex[component] = regex
		}
	}

	return leaf.append(path[1:])
}

func (node *node) search(path []string, vars map[string]string) *node {
	if len(path) == 0 {
		return node
	}

	leaf, pattern := node.getLeaf(path[0])
	if leaf == nil {
		return nil
	}

	if pattern != nil {
		vars[pattern[0]] = pattern[1]
	}

	return leaf.search(path[1:], vars)
}
