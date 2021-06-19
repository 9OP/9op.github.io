---
draft: false
toc: true
title: "Custom Go HTTP Router"
date: "2021-05-30"
readingTime: 30
tags: ["go", "backend", "http", "router"]
cover: "cover.jpg"
coverCaption: "© Christopher Burns"
---

<!--description-->

Ever wondered why there are so many Go HTTP routing libraries and frameworks out there? Well, I don't know myself, but I can help you create your
own Go HTTP routing library and make other developers wonder why there are so many Go HTTP routing libraries...

<!--more-->

You will also be able to benchmark your own router against other people's router because everybody knows that a router's performance is **SO** much
important and critical in a web API. 

Of course, I am being sarcastic (is this a good sign for a first article?). The truth is that router performance is almost always negligible compared
to IOs (databases, APIs ...), so why should it matters?. The Go standard `http.ServeMux` is said to not be performant, but this is not a concern. 
The main issue with it is that it only supports simple pattern matching. This is far more problematic than performance.

Why would you need to create your HTTP router instead of relying on a Go web framework? I see multiple rationals to do so:
- You don't need a full web framework but only a router supporting complex pattern matching
- You like to keep your code clear and clean and prefer a short dependency tree
- You need a modular router that you can extend
- Building an HTTP router is simple and easy to maintain.

I think building your router gives you more control over your web API and keep the dependency tree short and clean.
In my opinion, it makes more sense in the context of microservices where you rarely need to leverage the full capacity of a web framework. 


{{<linebreak 2>}}

**Sources on [GitHub](https://github.com/9OP/9op.github.io/tree/master/content/post/gorouter/src).**

{{<linebreak>}}

## Introduction

I started learning Go a few weeks ago and I liked the language and its philosophy. 
Go is a memory-safe statically typed compiled language, *almost* as performant as C! 
It was designed at Google by living legends (K. Thompson, R. Pike) to be performant and easy to use.

One of [Go proverbs](https://go-proverbs.github.io/) is "A little copying is better than a little dependency."
So I encourage you to copy and adapt the source code of this article if you need it.

>This blog post is divided in two parts to make it more "digest". The first part focuses on building a trie-based simple
>HTTP router. The second part focuses on extending the router build in the first part to support middlewares and complex
>pattern matching

{{<linebreak 3>}}

## Part 1 - Building the router
---

### Standard router

The Go standard HTTP router is good enough for simple routing pattern. However it does not support the complex pattern matching you would expect from
a web framework. For instance, there is not support for URL parameter, such as `/book/:id`
```go
func main() {
	http.HandleFunc("/", home)
	http.HandleFunc("/about", about)

	addr := fmt.Sprintf("localhost:%v", 8080)
	srv := &http.Server{
		Addr:    addr,
		Handler: http.DefaultServeMux,
	}
	log.Fatal(srv.ListenAndServe())
}

func home(w http.ResponseWriter, r *http.Request) {
	fmt.Fprint(w, "home\n")
}

func about(w http.ResponseWriter, r *http.Request) {
	fmt.Fprint(w, "about\n")
}
```

This is a simple web server with two routes: `/` and `/about`.
We can test the web server with `curl`:

```txt {linenos=false}
> $ curl localhost:8080/
home

> $ curl localhost:8080/about
about

> $ curl localhost:8080/about/
home

> $ curl localhost:8080/123
home
```

Some outputs are surprising. A request on `/about/` returns `home`, not `about` as one would expect. 
Same, a request on `/123`, which is not a declared endpoint, returns `home` and not a `404` error.

The default router is still fine for a small web API that only requires a simple routing strategy.
However, it comes short when one needs more. To support complex routing strategies we need to extend the default router.

{{<linebreak 3>}}

### Prefix tree
>A prefix tree, or trie, is a type of search tree, a tree data structure used for locating specific keys from within a set.
>
> **- [Wikipedia](https://en.wikipedia.org/wiki/Trie)**

A **trie** is the data structure that will allow our router to match HTTP request's URL to defined endpoints.
This data structure is relevant for a router since multiple endpoints share common predecessors elements. For instance the routes 
`/home`, `/home/about`, `/home/contact` all share the same `/home` component. The corresponding trie would be a node `/home` 
that points toward leaf nodes `/about` and `/contact`.

```txt {linenos=false}
/home
	↳ /about
	↳ /contact
```

We will need to implement our own version of a trie since it is not present in the standard library. The first step is to 
define the data structure of a trie. It is simply a chain of linked nodes.

```go
import "net/http"

type node struct {
	handlers map[string]http.Handler
	leaves 	 map[string]*node
}

func newNode() *node {
	return &node{
		handlers: map[string]http.Handler{},
		leaves:   map[string]*node{},
	}
}
```

The object `node` contains two fields. `handlers` which maps an HTTP method (`"GET"`, `"POST"`, `"PUT"`, `"DELETE"` ...) 
to an  `http.Handler` and `leaves` which maps a single URL path component (`/home`, `/about`, `/contact` ...) to a leaf `node`.

#### Append

We need to create a method to build the trie. Because this data structure is used dynamically by the `Router`, 
we need a function that can append dynamically (ie. at runtime) new endpoints to the trie.

```go 
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

func (node *node) getLeaf(v string) *node {
	if node, ok := node.leaves[v]; ok {
		return node
	}
	return nil
}
```

`append` is a `node` (recursive) method that takes a slice/array of path components (eg. `["/home", "/contact"]` for path `"/home/contact"`), 
create the leaves and return a reference to the node matching the given `path`. `getLeaf` is a simple utility method 
that returns a reference to the leaf node that match a path component.

#### Search

Then we need a function that return the node instance of a given path. This function is similar to append, it just does not create new leaves.

```go
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
```

The logic of `search` is similar to `append` since they both are [DFS traversal algorithm](https://en.wikipedia.org/wiki/Depth-first_search). 
In the case of `search`, the stopping condition returns the last reached leaf's handlers or returns nil if the path is not found.

{{<linebreak 3>}}

### Router

```go
type Router struct {
	trie *node
}

func NewRouter() *Router {
	return &Router{
		trie: newNode(),
	}
}
```

The object `Router` contains a head `node` reference to our routing trie. 
Later we are going to extend the `Router` to support middlewares.

`Router` needs two main methods to be used with the `net/http` package:
- A method to map a handler to a endpoint
- A method to serve an HTTP request

#### Handle

```go
func (router *Router) Handle(path, method string, h http.Handler) {
	node := router.trie.append(split(path))
	node.handlers[method] = h
}

func split(path string) []string {
	path = strings.TrimSpace(path)
	path = strings.TrimPrefix(path, "/")
	path = strings.TrimSuffix(path, "/")
	return strings.Split(path, "/")
}
```

`Handle` method first append the endpoint `path` to the router's trie. Then it maps the `method` to the `h http.Handler`.
We use `split`, a simple utility function, that returns a trimmed slice of components from a path (eg. `split("/home/contact/") = ["home", "contact"]`).

#### ServeHTTP

```go
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
```

`ServeHTTP` executes the relevant handler for each requests. The `defer func()` block allows to catch every panic (ie. Go exceptions) from sub modules and 
return a clean `500 - server error` reponse to the clients without crashing the service. `handler` is initizalized with `NotFoundHandler`. 
If the router is able to match the request then `handler` is overiden by the found handler. Finally, `match` is a wrapper arround the 
router's trie `search` method. It just returns the associated handler of a request if the path exists in the router's trie. 

{{<linebreak >}}

We now have every necessary elements for a our base `Router`. Let's have a look on the trie-hierarchy for the following routes:
- `GET /book`
- `POST /book`
- `GET /book/:id`
- `DELETE /book/:id`
- `PUT /book/:id`
- `POST /book/:id/borrow`
- `GET /book/:id/borrow`
- `PUT /book/:id/borrow/:id`
- `GET /book/author/:id`

These corresponds to a simple CRUD API endpoints to create and borrow books. The corresponding trie is:

```txt {linenos=false}
>$ go run .
↳ head  				[]
	↳ book  			[POST GET]
        ↳ author  		[]
        	↳ :id 		[GET]
    	↳ :id			[GET DELETE PUT]
        	↳ borrow	[POST GET PUT]
```

Each line shows the handlers keys associated to a specific node. The node `book -> author` does not contain
any keys as it is not a defined endpoint. The node `/book/:id/borrow` contains handlers for the methods `POST, GET, PUT`

{{<linebreak 3>}}

### Usage

Usage is straightforward, simply instantiate a router and pass it as the root handler of the server:

```go
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
```

This router fix the caveats found in the standard router:

```txt {linenos=false}
> $ curl localhost:8080/home
home

> $ curl localhost:8080/about
about

> $ curl localhost:8080/about/
about

> $ curl localhost:8080/123
404 not found
```

This router is a nice base, but it still lacks important features such as middleware support and complex routing pattern.


{{<linebreak 3>}}

## Part 2 - Extending the router
---

In this part we focuses on extending the router built on Part 1. I will guide you to refactor the base router to support middlewares 
and complex pattern matching. 

### URL parameters

The URL parameters correspond to elements/components of the URL path that are dynamic. For instance `/book/:id`, where `:id` is a URL-safe parameter (eg. a number) 
used to identify a `book` entity. Our router should be able to parse `:id` and pass the values to the handler.

On top of that we would also like to provide a validation schema for this parameter. 
For instance `:id` could only be a number between 0 and 9. This is how I would like to declare the endpoint:
```go
func main() {
	router := NewRouter()

	// the URL parameter format follows /:name:regex
	router.Handle("/book/:id:^[0-9]$", "GET", http.HandlerFunc(home))

	// ...
}
```
The feature is not completly straightforward because we actually need two mechanisms:
- Parsing and matching of regular expressions
- Passing custom parsed values from the router to handlers

#### Parse

First the router's trie needs a new field for mapping regular expressions to URL components.
This new field is `regex` which maps a string (eg. `:id`) to a regex (eg. `^[0-9]$`)

```go 
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
```

The node structure has changed so we need to update the methods of to use the new `regex` field. 

`getLeaf` function returns a node's leaf or nil, matching an URL component. With the support of URL-parameter, `getLeaf` 
should also look for matching regular expression. 

If argument `v` is not found in the node's `leaves` then it is looked for in the node's `regex`. 
If a regex match, then the leaf whose mapped to the 'regex key' is returned along with the URL parameter name and value.

```go
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
```

For instance, given the following node and `v=5`, `getLeaf` would return `*node, map[id: 5]`:

```txt {linenos=false}
{
	handlers:   []
	leaves:     {':id': *node }
	regex:      {':id': '^[0-9]$'}
}
```

Then we need to update the node `append` method to look for complex pattern and create the regex.

```go
func parse(c string) (string, *regexp.Regexp) {
	if string(c[0]) == ":" {
		// Given c=":id:^[0-9]$", then pattern=["id" "^[0-9]$"]
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
```

The `append` method is similar to the previous version. We just added a new condition to handle regex elements contained in the `path` argument.
In the case a path element is a regex, then the function `parse` returns the value of the element and a compiled regex.

#### Match

Now that the router is able to create paths containing complex pattern (eg. `/book/:id:^[0-9]$`), we need a way to pass the matched URL parameters
from the router to the handlers. For that we will use the `context` standard library. Context allow the creation of 'request scoped' context for 
defining variables, deadlines, etc... In short, a context is a collection of meta data and methods, attached to a specific request.

We first implement a `Vars` method that will return the `"vars"` value of a request context. This function will be used to get the 
URL parameters inside the handlers.

```go
func Vars(r *http.Request) map[string]string {
	if vars := r.Context().Value("vars"); vars != nil {
		return vars.(map[string]string) // type cast
	}
	return nil
}
```

For instance, given:
- Endpoint: `/home/:id:^[0-9]$`
- Request: `/home/5`

The `Vars` function would return `map["id": "5"]`

Then we update the `ServeHTTP` and `match` methods to use the context variable "vars".

```go
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
```

Finally, the node method `search` append the parsed URL parameters in the `vars` map when a pattern is found.

```go
func (node *node) search(path []string, vars map[string]string) *node {
	if len(path) == 0 {
		return node
	}

	leaf, pattern := node.getLeaf(path[0])
	if leaf == nil {
		return nil
	}

	if pattern != nil {
        // given endpoint /:id:^[0-9]$ and request /5
        // pattern[0]= "id" pattern[1]= "5"
		vars[pattern[0]] = pattern[1]
	}

	return leaf.search(path[1:], vars)
}
```

{{<linebreak >}}

The feature is complete, we are able to test it with a simple web server:

```go
func main() {
	router := NewRouter()
	http.Handle("/", router)

	router.Handle("/book/:id:^[0-9]{1,3}$", "GET", http.HandlerFunc(book))

	// ListenAndServe
}

func book(w http.ResponseWriter, r *http.Request) {
	vars := Vars(r)
	fmt.Fprintf(w, "book: %s \n", vars["id"])
}
```

Few examples:

```txt {linenos=false}
> $ curl localhost:8080/home/456
book: 456

> $ curl localhost:8080/home/3
book: 3

> $ curl localhost:8080/home/abc
404 page not found

> $ curl localhost:8080/home/1234
404 page not found
```

The server returned a `NotFound` error for the requests with `:id` that was not a sequence of 1-to-3 digits.

{{<linebreak 3>}}

### Middlewares

Middlewares are very common when designing web services. They are basically piece of logic that lies between the a router and a handler.
The following application logic are usually carried via middlewares:
- CORS
- User authentication / authorization
- Logging / monitoring
- Translation

A middleware function signature is just `func middleware(h http.Handler) http.Handler`. 
It simply is a function that takes a handler and return a decorated handler. Nothing more.

Because the signature is "bijective", it is easy to chain middlewares along.

The first step is to extend the router object and define a `middleware` type.
Then we create a new router method `Use` that append a middleware to a router instance.

```go
type middleware = func(h http.Handler) http.Handler

type Router struct {
	trie        *node
	middlewares []middleware
}

func NewRouter() *Router {
	return &Router{
		trie:        newNode(),
		middlewares: [*middleware{},
	}
}

func (router *Router) Use(m middleware) {
	router.middlewares = append(router.middlewares, m)
}
```

Finally, the last step is to apply the middleware to the handler:

```go
func (router *Router) ServeHTTP(w http.ResponseWriter, r *http.Request) {
    // defer...
	handler := http.NotFoundHandler()

	if h := router.match(r); h != nil {
		handler = h

		// Apply middlewares
		for _, m := range router.middlewares {
			handler = m(handler)
		}
	}

	handler.ServeHTTP(w, r)
}
```

{{<linebreak>}}

The feature is complete, we can test it with a simple web server:

```go
func main() {
	router := NewRouter()
	router.Handle("/home", "GET", http.HandlerFunc(home))
	
	router.Use(helloMiddleware)
	// ... ListenAndServe
}

func home(w http.ResponseWriter, r *http.Request) {
	fmt.Fprint(w, "hello world!\n")
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
```

An example:

```txt {linenos=false}
> $ curl localhost:8080/home                      

I am a middleware!
hello world!
Bip bip bop!
```

As expected, the handler `home` was surrounded by the middleware writings.

This is a silly example. The point of a middleware is to perform intermediate logics before and after handlers. This is convenient because joined with 
context, middlewares can append new context variables to the requests before they reache the handlers.

Typically, this is used when authenticating user. A user is authenticated by a middleware, then the user entity is passed to the handlers via a context variable.

A dummy authentication middleware would look like:

```go
func Authentication(h http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if t := r.Header.Get("token"); t != "SECRET-ACCESS-TOKEN" {
			w.WriteHeader(http.StatusUnauthorized)
			return
		}
        w.Write([]byte("Authorized\n"))
		h.ServeHTTP(w, r)
	})
}
```

And return the following reponses:

```txt {linenos=false}
> $ curl localhost:8080/home
401 Unauthorized

> $ curl -H "token: SECRET-ACCESS-TOKEN"  localhost:8080/home
Authorized
```

{{<linebreak 3>}}

## Conclusion

Go philosophy and community advocate simplicity and minimizing dependency when possible.
It does not mean one should feel guilty for relying on an external library, however, it means one should always
carefully evaluate the tradeoffs of using a lib.

In this article, we have implemented a tri-based router, that allows more complex routing pattern than
the Go standard router, without relying on an external routing package.
Creating a custom router is simple and the implementation is no more than 200 LOC which makes it easy to maintain in the long term.
