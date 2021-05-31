
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
With the support of URL-parameter, `isLeaf` should also look for matching regular expression. If argument `v` is not found in the `node`'s leaves mapping `l`, 
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
