## Standard router

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

Some outputs are surprising. A request on `/about/` returns `home`, not `about` as one would expect. 
Same, a request on `/123`, which is not a declared endpoint, returns `home` and not a `404` error.

The default router is still fine for a small web API that only requires a simple routing strategy.
However, it comes short when one needs more. To support complex routing strategies we need to extend the default router.

{{<linebreak 3>}}

## Prefix tree
>A prefix tree, or trie, is a type of search tree, a tree data structure used for locating specific keys from within a set.
>
> **- [Wikipedia](https://en.wikipedia.org/wiki/Trie)**

A **trie** is the data structure that will allow our router to match HTTP request's URL to defined endpoints.
This data structure is relevant for a router since multiple endpoints share common predecessors elements. For instance the routes 
`/home`, `/home/about`, `/home/contact` all share the same `/home` component. The corresponding trie would be a node `/home` 
that points toward leaf nodes `/about` and `/contact`.

```txt
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

### Append

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

### Search

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

## Router

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

### Handle

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

### ServeHTTP

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

```txt
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

## Usage