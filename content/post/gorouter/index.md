---
draft: false
toc: true
layout: "single"
type: "post"
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
to IOs (databases, APIs ...). The Go standard `http.ServeMux` is said to not be performant, but this is not a concern. The main issue with it
is that it only supports simple pattern matching. This is far more problematic than performance.

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

{{<linebreak 3>}}

## Part 2 - Extending the router
---

{{<linebreak 3>}}

## Conclusion

conclusion
