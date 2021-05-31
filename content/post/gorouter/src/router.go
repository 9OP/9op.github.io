package main

import (
	"net/http"
	"strings"
)

func split(path string) []string {
	path = strings.TrimSpace(path)
	path = strings.TrimPrefix(path, "/")
	path = strings.TrimSuffix(path, "/")
	return strings.Split(path, "/")
}

type Router struct {
	trie *node
	// ...
}

func NewRouter() *Router {
	return &Router{
		trie: newNode(),
	}
}

func (router *Router) Handle(path, method string, h http.Handler) {
	node := router.trie.append(split(path))
	node.handlers[method] = h
}

func (router *Router) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	defer func() {
		if err := recover(); err != nil {
			http.Error(w, "server error", http.StatusInternalServerError)
		}
	}()

	handler := http.NotFoundHandler()

	if h := router.match(r); h != nil {
		handler = h
	}
	handler.ServeHTTP(w, r)
}

func (router *Router) match(r *http.Request) http.Handler {
	if node := router.trie.search(split(r.URL.Path)); node != nil {
		return node.handlers[r.Method]
	}
	return nil
}
