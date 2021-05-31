---
draft: true
toc: true
title: "Custom Go HTTP Router"
date: "2021-05-22"
readingTime: 25
tags: ["go", "backend", "http", "router"]
cover: "img/routes.jpg"
coverCaption: "© Christopher Burns"
---

<!--description-->

Ever wondered why there are so many Go routing libraries out there? Well, I don't know myself, but I've read *somewhere* that 
this is because the standard Go router (yes the one in `net/http`) is not a good one because it is not performant or does not provide enough features.

I will not talk about router performance because this is bullshit, routing time is **LARGELY** negligeable compared to IOs (database, APIs...).
You surely do not need full a third party router for your use case but the Go router has some caveats you want to avoid?

In this case you find the right article! In this post we are going to build a simple trie-based router that you will be able to customize to your needs.

<!--more-->

{{<linebreak 3>}}

## Introduction

I started learning and using Go a few weeks ago and I completly felt in love with the language and its philoshophy.
Go advocates simplicity and explicity. It is a memory-safe statically typed compiled language, *almost* as performant
as C! Go was design at Google by living legends (namely K. Thompson, R. Pike) to be performant and easy to use.

One of [Go proverbs](https://go-proverbs.github.io/) is "A little copying is better than a little dependency." 
Coming from the JavaScript world where there is a dependancy for everything 
(even some ridiculous 2 lines long `isOdd` dependancy), this is refreshing.

The Golang community does not suffer the same problem. Mainly because the community is many times smaller than the JavaScript
community, so there is fewer brain time to reinvent the wheel again and again. 
But also because the language itself advocates in his philosophy to avoid unecessary bloated dependencies.

I don't know about you, but personnally I prefer my code to rely on fewer dependencies, even if I have to implement more application logic. 
We developer are looking for control, for safety, for trust and this is easier to achieve with a pragmatic dependancy policy. 

Why would you need to maintain your own HTTP router? 
- You think the default Go router does not provide enough possibilities
- You do not want to include a dependancy in your app
- You need a custom router with specific routing capabilities

I will be 100% honest with you. I don't think you really need a custom router. I truly think the Go default router is 
good enough for the majority of our use case. However, I understand that developing its own router is appealling because of the
control it offers. So here we are.

>In this blog post, I propose a simple trie-based router implementation in order to keep your HTTP service dependance's free.

{{<linebreak 3>}}

## Standard router

Go standard HTTP router is good enough for simple routing pattern. However it does not support complex pattern matching like you could expect from
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
```txt
> $ curl localhost:8080/
home

> $ curl localhost:8080/about
about

> $ curl localhost:8080/about/
home

> $ curl localhost:8080/123
home
```
Some outputs are surprising. A request on `/about/` returns `home`, not `about` as one could expect. Same, a request on `/123`, which is not a declared endpoint, still returns `home` and not
some `404` error.

These caveats can be mitigated easily:
- First, you might change the endpoint `/` for `/api` or `/home`. In that case there is not failling back route and you will get `404` if a request does not match.
- Second, the trailling `/` in `/about/` can be fixed with a simple trimming function

the default router is still fine for small web app that require only a simple routing strategy.
But it comes short when one need more. 

{{<linebreak 3>}}

## Prefix tree
>A prefix tree, or trie, is a type of search tree, a tree data structure used for locating specific keys from within a set.
>
> **- [Wikipedia](https://en.wikipedia.org/wiki/Trie)**

A **trie** is the data structure that will allow our router to match HTTP request URL to our predefined route endpoints.
This data structure is relevant for a router since multiple endpoints share common route elements. For instance routes 
`/home`, `/home/about`, `/home/contact` share the same `/home` component.

This tree-view is represented by a node `/home` that points towards leafs `/about` and `/contact`.


### Trie node
```go
import "net/http"

type node struct {
	h map[string]http.Handler
	l map[string]*node
}
```
The `node struct` contains two unexported members: `h` which maps a HTTP method (GET, POST, PUT, DELETE ...) 
to a handler and `l` which links the node to its leafs.
```go
func newNode() *node {
	return &node{
		h: map[string]http.Handler{}, 
		l: map[string]*node{},
	}
}

func (node *node) isLeaf(v string) *node {
	if node, ok := n.l[v]; ok {
		return node
	}
	return nil
}
```
Then `func newNode` simply returns a pointer to an initialized `node` instance, and `func isLeaf` returns either `nil` or a `*node` correponding to the leaf matching the the path component `v`.


### Trie append
Now we need to create a method to build the trie. Because this data structure is used dynamically by the `Router`, 
we need a function that can append dynamically new endpoints to the trie.

There are multiple approaches to implement such function. I propose a recursive implementation because it is more explicit in my opinion.
```go 
func (node *node) append(path string) *node {
	recursive := func(n *node, p []string) {
		// Stop condition
		if len(p) == 0 {
			return n
		}
		component := p[0]

		leaf := n.isLeaf(component)
		if leaf == nil {
			n.l[component] = newNode(component)
			leaf = n.l[component]
		}
		return recursive(leaf, p[1:])
	}

	return recursive(t, split(path))
}
```
`append` is a `node` method. It takes a path as argument (eg. `/home/about/team`). The inner lambda function `recursive` takes a `*node` and a slice of string containing the different component of the path (eg. `["home" "about" "team"]`).

The recursive function simply takes the first component element then assess its existence in the current node's leafs. If the component is in the node's leafs then `recursive` call itself with the leaf and the `p` slice re-sliced. Otherwise, a new leaf with value `component` is appended to the node.

`splitPath` is a simple utility function that returns a slice of the path's components.
```go
import "strings"

// "/home/resource/id/" -> ["home", "resource", "id"]
func split(path string) []string {
	path = strings.TrimSpace(path)
	path = strings.TrimPrefix(path, "/")
	path = strings.TrimSuffix(path, "/")
	return strings.Split(path, "/")
}
```

### Trie search
The last piece we need is a search/match function. The role of this function is to retrieve the approriate handler for a specific request's URL. Same as for the `append` function, a recursive approach is simpler.
```go
func (node *node) search(path string) map[string]http.Handler {
	recursive := func(n *node, p []string) {
		// Stop condition
		if len(p) == 0 {
			return n.h
		}

		leaf := n.isLeaf(p[0])
		if leaf == nil {
			return nil
		} else {
			return recursive(leaf, p[1:])
		}
	}

	return recursive(n, split(path))
}
```
The logic of `search` is similar to `append` since they both are trie traversal algorithm. In the case of `search`, the stopping condition returns the last reached leaf's handlers or returns nil if the path is not found.

{{<linebreak 3>}}

## Router
```go
type Router struct {
	t *node
	// ...
}
```
A `Router` is an object that contains the head `*node` of our routing trie. Later we are going to extend the `Router` to support middlewares.

The `Router` needs to implement two methods in order to be used with the `net/http` package. It needs a `Handle` method, that allows registering endpoints and handlers. And it needs a `ServeHTTP` method, in order to match requests' URL and serve the correct handlers.

```go
func (router *Router) Handle(path string, method string, handler http.Handler) {
	node := router.t.append(path)
	node.h[method] = handler
}
```
`Handle` simply append the path to the trie and add a new key val association `method: handler` to the `node` handlers. 
```go
func (router *Router) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	defer func() {
		if err := recover(); err != nil {
			http.Error(w, "server error", http.StatusInternalServerError)
		}
	}()

	var handler http.Handler = http.NotFoundHandler()

	if h := router.match(r); h != nil {
		handler = h
	}
	handler.ServeHTTP(w, r)
}
```
`ServeHTTP` is responsible for executing the relevant handler for each request. The `defer func()` block allows to catch every panic from sub modules and return a clean `500 - server error` reponse to the clients without crashing the service.

Then `handler` is initizalized with `NotFound`. If the `router` is able to match the request `r` then the handler is overiden by the found handler.

```go
func (router *Router) match(r *http.Request) http.Handler {
	if h := router.t.search(r.URL.Path); h != nil {
		return h[r.Method]
	}
	return nil
}
```
`match` search in the `router.t` trie the request's URL. If the trie has a matching `map[string]http.Handler`, then match return the entry associated to the request method. If `h` does not have an entry for `r.Method`, it will return `nil`.

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

These corresponds to a simple CRUD API endpoints to create and borrow books.
With a simple graph traversing (BFS) we get the following view of our router trie:

```txt
>$ go run .
↳ head  				[]
	↳ book  			[POST GET]
        ↳ author  		[]
        	↳ :id 		[GET]
    	↳ :id			[GET DELETE PUT]
        	↳ borrow	[POST GET PUT]
```

The traversall shows the hierarchy of URL's components. Each line shows the handlers keys associated to a specific node. The node `book -> author` does not contain
any keys as it is not a defined endpoint. The node `book -> :id -> borrow` contains handlers for the methods `POST, GET, PUT`

***Note:** we have not seen yet how to handle URL parameters (such as `:id`). We will see this later on extending the `Router`.*

{{<linebreak 3>}}

## Server
```go
import (
	"log"
	"net/http"
)

func main() {
	// Create a new Router
	router := NewRouter()

	// Attach first route
	router.Handle("/home", "GET", http.HandlerFunc(home))

	// Attach router to the DefaultServeMux
	http.Handle("/", router)
	
	// Start server
	addr := fmt.Sprintf("localhost:%v", 8080)
	srv := &http.Server{
		Addr:    addr,
		Handler: http.DefaultServeMux,
	}
	log.Printf("Start server on: %v", addr)
	log.Fatal(srv.ListenAndServe())
}

func home() { 
	w.Write([]byte("Hello World\n"))
}
```
We use the `DefaultServeMux` but we could also have used a `http.NewServeMux()`. The difference is that other library can add handler to the `DefaultServeMux` while
the `NewServeMux` grant you complete control over the handlers you want. Adding a new endpoint is as simple as calling `router.Handle('/endpoint', 'METHOD', handler)`.

The server output the data correctly:
```txt
> $ curl -i localhost:8080/home 

HTTP/1.1 200 OK
Date: Thu, 27 May 2021 21:04:11 GMT
Content-Length: 11
Content-Type: text/plain; charset=utf-8

Hello World
```

{{<linebreak 3>}}

## Extending the Router
The `Router` is ready for some new feature. For instance URL parameters, or middlewares. These are easy to add to our data structure.

### URL parameters
The URL parameters correspond to elements/components of the URL that are dynamic. For instance `/book/:id`, where `:id` is a URL-safe parameter (eg. a number) 
used to identify a `book` entity. Our router should be able to parse `:id` and pass the values to the handler.

On top of that we would also like to provide a validation schema for this parameter. 
For instance `:id` could only be a number between 0 and 9. This is how we would declare the route:
```go
func main() {
	router := NewRouter()

	// the URL parameter format follows /:name:regex
	router.Handle("/book/:id:^[0-9]$", "GET", http.HandlerFunc(home))

	// ...
}
```
The feature is not completly straightforware because we actually need two mechanisms:
- Parsing and matching of regular expressions
- Passing custom parsed values from Router to handlers

#### Parsing regex
First the `Router`'s trie need a new field for mapping regular expressions to URL components.
This new field is `r` which maps a string (eg. `:id`) to a regex (eg. `^[0-9]$`)
```go 
type node struct {
	h map[string]http.Handler
	l map[string]*node
	r map[string]*regexp.Regexp
}

func newNode() *node {
	return &node{
		map[string]http.Handler{},
		map[string]*node{},
		map[string]*regexp.Regexp{},
	}
}
```
We need to update the methods of `node` to use this new field. `isLeaf` function returns a node's leaf or nil, matching an URL component.
With the support of URL-parameter, `isLeaf` should also look for matching regular expression. If argument `v` is not found in the `node`'s leafs mapping `l`, 
then it is looked for in the `node`'s regular expressions mapping `r`. If a regex match, then the node whose value is 'regex mapping key' is returned along with the URL parameter name and value.
```go
func (n *node) isLeaf(v string) (*node, []string) {
	if node, ok := n.l[v]; ok {
		return node, nil
	}
	for key, re := range n.r {
		if re.MatchString(v) {
			return n.l[key], []string{key, v}
		}
	}
	return nil, nil
}
```
For the following node and `v=5`, `isLeaf` would return `*node, map[id: 5]`:
```txt
{
	h: []
	l: {':id': *node }
	r: {':id': '^[0-9]$'}
}
```

Finally, the `append` method need to create the mapping of `:id` to `^[0-9]$` when recursively creating the trie.
```go
func parseComponent(c string) (string, *regexp.Regexp) {
	if string(c[0]) == ":" {
		// Given c=":id:^[0-9]$", then pattern=[":id" "^[0-9]$"]
		pattern := strings.Split(c[1:], ":")
		if re, err := regexp.Compile(pattern[1]); err == nil {
			return patterm[0], re
		}
	}
	return c, nil
}

func (node *node) append(path []string) *node {
	if len(path) == 0 {
		return node
	}
	component, regex := parseComponent(path[0])
	leaf, _ := node.isLeaf(component)
	if leaf == nil {
		node.l[component] = newNode()
		leaf = node.l[component]

		if regex != nil {
			node.r[component] = regex
		}
	}
	return leaf.append(path[1:])
}
```

In the case a path elements is a regex, then the `parseComponent` returns the value of the component name as a string and the
associated compiled regex.

Now our `Router` support URL-parameter and regex in the `router.Handle(...)` function. Then we need a way to pass matched request's URL
elements to the Handlers. For that we will use the `context` standard library.

#### Matching parameters

`context` offers many features such as request deadline, cancellation, scope etc...
For our use case we will use `context` to attach the parsed URL parameters to the `r *http.Request` object.
First we define the context key:
```go
import "context"

type contextKey string
var contextVars = contextKey("vars")
```
Then we need a function that fetch the `contextVars` object from the `r *http.Request` object:
```go
func Vars(r *http.Request) map[string]string {
	if vars := r.Context().Value(contextVars); vars != nil {
		return vars.(map[string]string) // type cast
	}
	return nil
}
```
Note that the returned value is `map[string]string`. For the following:
- Endpoint: `/home/:id:^[0-9]$`
- Request: `/home/5`

The `Vars` function would return `map["id": "5"]`

Then we create the `vars` map in the `Router.ServeHTTP` function. This map is passed to the `match` function
and to the `node.search` method.
```go
func (router *Router) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	// defer ...
	handler := http.NotFoundHandler()
	vars := map[string]string{}

	if h := router.match(r, vars); h != nil {
		handler = h
	}

	ctx := context.WithValue(r.Context(), contextVars, vars)
	handler.ServeHTTP(w, r.WithContext(ctx))
}

func (router *Router) match(r *http.Request, v map[string]string) http.Handler {
	if node := router.t.search(split(r.URL.Path), v); node != nil {
		return node.h[r.Method]
	}
	return nil
}
```
The updated `node.search` method simply update the `vars` map when a pattern is found.
```go
func (node *node) search(path []string, vars map[string]string) *node {
	if len(path) == 0 {
		return node
	}

	leaf, pattern := node.isLeaf(path[0])
	if leaf == nil {
		return nil
	}

	if pattern != nil {
		vars[pattern[0]] = pattern[1]
	}

	return leaf.search(path[1:], vars)
}
```
The feature is complete. Our custom router can now handle URL parameter parsing with regex validation:
```go
func main() {
	router := NewRouter()
	http.Handle("/", router)

	router.Handle("/home/:id:^[0-9]{1,3}$", "GET", http.HandlerFunc(home))

	// ListenAndServe
}

func home(w http.ResponseWriter, r *http.Request) {
	vars := Vars(r)
	fmt.Fprintf(w, "Hello world: %s \n", vars["id"])
}
```

A few curl example returns:
```txt
> $ curl -i localhost:8080/home/456

HTTP/1.1 200 OK
Date: Sat, 29 May 2021 14:06:09 GMT
Content-Length: 18
Content-Type: text/plain; charset=utf-8

Hello world: 456 
```

The request returned a success with the parsed URL parameter in the reponse body.

```txt
> $ curl -i localhost:8080/home/1234

HTTP/1.1 404 Not Found
Content-Type: text/plain; charset=utf-8
X-Content-Type-Options: nosniff
Date: Sat, 29 May 2021 14:35:17 GMT
Content-Length: 19

404 page not found
```

The request returned a `NotFound` error because the `:id` is `1234` which does not 
match the regex `^[0-9]{1,3}$`


### Middleware
Middlewares are very common when designing web services and HTTP APIs. The are basically piece of logic that lies between the `Router` and the `Handlers`.
The following logics are usually carried via middleware in web APIs:
- CORS
- User authentication / authorization
- Logging / monitoring
- Translation

A middleware signature is straightforware: `func middleware(h http.Handler) http.Handler`. It simply is a function that takes a handler
and return a decorated handler.

In order to add support for middlware, we have to modify the `Router struct`. 
```go
type middleware = func (h http.Handler) http.Handler

type Router struct {
	t *node
	m []middleware
}
```
`m` is a slice that contains references to middlewares.

Then we need to apply the middleware to the requests. This is carried by the `Router` `ServeHTTP` function:
```go
func NewRouter() *Router {
	return &Router{
		t: newNode(),
		m: []middleware{},
	}
}

func (router *Router) Use(m middleware) {
	router.m = append(router.m, m)
}

// func (router *Router) Handle...
// func (router *Router) match...

func (router *Router) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	// defer...
	var handler http.Handler = http.NotFoundHandler()

	if h := router.match(r); h != nil {
		handler = h

		// Apply middlwares
		for _, m := range router.m {
			handler = m(handler)
		}
	}

	handler.ServeHTTP(w, r)
}
```
We can now simply use a middleware with the `Router.Use` method.
```go
func main() {
	router := NewRouter()
	
	router.Handle("/home", "GET", http.HandlerFunc(home))
	
	router.Use(helloMiddleware)
	// ...
}

func helloMiddleware(h http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte("I am a middleware!\n"))
		h.ServeHTTP(w, r)
		w.Write([]byte("Bip bip bop!\n"))
	})
}
```
The request at `/home` gives:
```txt
> $ curl -i localhost:8080/home                      
HTTP/1.1 200 OK
Date: Thu, 27 May 2021 21:09:40 GMT
Content-Length: 36
Content-Type: text/plain; charset=utf-8

I am a middleware!
Hello World
Bip bip bop!
```

This is a silly example, the point being that the middlewares can access the `w http.ResponseWriter, r *http.Request` objects and wrap handlers' logic.

Global middlwares are applied to the router with `router.Use(...)`. Global router make sense for logging, CORS, throttling... Middlewares can also be applied locally to specific endpoints, which is usefull for authentication for instance:
```go
func main() {
	router := NewRouter()
	router.Handle("/home", "GET", Authentication(http.HandlerFunc(home)))
	http.Handle("/", router)
	// ...
}

func Authentication(h http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if t := r.Header.Get("token"); t != "SECRET-ACCESS-TOKEN" {
			w.WriteHeader(http.StatusUnauthorized)
			return
		}
		h.ServeHTTP(w, r)
	})
}

func home() { 
	w.Write([]byte("Hello World\n"))
}
```
Which gives us:
```txt
> $ curl -i localhost:8080/home

HTTP/1.1 401 Unauthorized
Date: Thu, 27 May 2021 22:03:24 GMT
Content-Length: 5
Content-Type: text/plain; charset=utf-8
```
and
```txt
> $ curl -i -H "token: SECRET-ACCESS-TOKEN"  localhost:8080/home

HTTP/1.1 200 OK
Date: Thu, 27 May 2021 22:04:46 GMT
Content-Length: 17
Content-Type: text/plain; charset=utf-8

Hello World
```


{{<linebreak 3>}}

## Conclusion

Go philosophy and community advocates simplicity, explicity and minimizing dependancy when possible.
It does not mean one should feel guilty for relying on external library, however it means one should always
evaluate the needs and tradeoffs of using a lib.

In this article we have implemented a tri-based router, that allows more complex routing pattern than
the Go standard router, without relying on external routing package.
Creating a custom router is simple and the implementation is no more than 200 LOC which makes it maintainable in the long term.
