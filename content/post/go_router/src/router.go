package main

import (
	"context"
	"net/http"
	"strings"
)

func split(path string) []string {
	path = strings.TrimSpace(path)
	path = strings.TrimPrefix(path, "/")
	path = strings.TrimSuffix(path, "/")
	return strings.Split(path, "/")
}

type middleware = func(h http.Handler) http.Handler

type Router struct {
	trie        *node
	middlewares []middleware
}

func NewRouter() *Router {
	return &Router{
		trie:        newNode(),
		middlewares: []middleware{},
	}
}

func (router *Router) Use(m middleware) {
	router.middlewares = append(router.middlewares, m)
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
	vars := map[string]string{}

	if h := router.match(r, vars); h != nil {
		handler = h
		for _, m := range router.middlewares {
			handler = m(handler)
		}
	}

	ctx := context.WithValue(r.Context(), "vars", vars)
	handler.ServeHTTP(w, r.WithContext(ctx))
}

func (router *Router) match(r *http.Request, vars map[string]string) http.Handler {
	if node := router.trie.search(split(r.URL.Path), vars); node != nil {
		return node.handlers[r.Method]
	}
	return nil
}

func Vars(r *http.Request) map[string]string {
	if vars := r.Context().Value("vars"); vars != nil {
		return vars.(map[string]string) // type cast
	}
	return nil
}
