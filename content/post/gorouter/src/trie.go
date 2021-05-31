package main

import "net/http"

type node struct {
	handlers map[string]http.Handler
	leaves   map[string]*node
}

func newNode() *node {
	return &node{
		handlers: map[string]http.Handler{},
		leaves:   map[string]*node{},
	}
}

func (node *node) getLeaf(v string) *node {
	if node, ok := node.leaves[v]; ok {
		return node
	}
	return nil
}

func (node *node) append(path []string) *node {
	if len(path) == 0 {
		return node
	}
	component := path[0]

	leaf := node.getLeaf(component)
	if leaf == nil {
		node.leaves[component] = newNode()
		leaf = node.leaves[component]
	}

	return leaf.append(path[1:])
}

func (node *node) search(path []string) *node {
	if len(path) == 0 {
		return node
	}

	leaf := node.getLeaf(path[0])
	if leaf == nil {
		return nil
	}

	return leaf.search(path[1:])
}
