package main

import (
	"fmt"
	"log"
	"net/http"
)

func main() {
	router := NewRouter()

	router.Handle("/home", "GET", http.HandlerFunc(home))
	router.Handle("/about", "GET", http.HandlerFunc(about))
	router.Handle("/book/:id:.*", "GET", http.HandlerFunc(book))

	router.Use(helloMiddleware)

	http.Handle("/", router)

	addr := fmt.Sprintf("localhost:%v", 8080)
	srv := &http.Server{
		Addr:    addr,
		Handler: http.DefaultServeMux,
	}
	log.Printf("Start server on: %v", addr)
	log.Fatal(srv.ListenAndServe())
}

func home(w http.ResponseWriter, r *http.Request) {
	fmt.Fprint(w, "home\n")
}

func about(w http.ResponseWriter, r *http.Request) {
	fmt.Fprint(w, "about\n")
}

func book(w http.ResponseWriter, r *http.Request) {
	vars := Vars(r)
	fmt.Fprintf(w, "book: %s\n", vars)
}

func helloMiddleware(h http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// before the handler is executed
		w.Write([]byte("I am a middleware!\n"))

		h.ServeHTTP(w, r)

		// after the handler is executed
		w.Write([]byte("Bip bip bop!\n"))
	})
}
