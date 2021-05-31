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
