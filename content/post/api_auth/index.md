---
draft: true
toc: true
layout: "single"
type: "post"
title: "Secure API authentication"
date: "2021-06-19"
readingTime: 15
tags: ["python", "flask", "api", "authentication", "backend"]
cover: "cover.jpg"
coverCaption: "© Christopher Burns"
---

<!--description-->

API authentication is a critical component of any web service because it impacts the security of the users' data. It is not a topic to be overlooked
and though you may find many tutorials on the web about this, most of them avoid the security question and just copy paste each other.
I am writting this post, so from now on, it can be copy pasted by other wannabe tech guru and actually spread usefull information...


This is **NOT** *another JSON web tokens authentication API tutorial*, here we are going to ask the right questions and think security first. 

<!--more-->

{{<linebreak 2>}}

## Introduction

The context of this post is a backend API for a web app (Angular, React, Vue etc...).
In the context of a public API to be consummed by other web services (not web clients), the approach might be different, and we even might use JWT.

This post is about discussing the security vulnerabilities (mostly XSS and CSRF) when implementing an authentication mechanism for a web API.


## Authentication mechanism

Before diving into the technical questions about security and implementation, let's present a generic approach to authentication.

{{<figure src=authentication-mechanism.png caption=`Authentication mechanism flow diagram` >}}

The authentication mechanism consists in:
- A client sending his credentials to the server.
- The server verifying if the crendentials match an existing identity.
- The server generating an authentication proof send it back to the client.
- The client sending his authentication proof with futur requests etc... 

This mechanism is generic and correponds to many kind of implementations. Especially the implementation answers the following questions:
- How are the credentials send to the server? (Json, multi-form, basic auth ...)
- How the server match existing identity?
- What kind of authentication proof, the server generates?
- How the client (web browser) stores the authentication proof?

The secure implementation of this mechanism, is the purpose of this post.

{{<linebreak >}}

## Vulnerabilities

Since we are going to talk about security, we need to get familiar with the two main vulnerabilities this article is about: XSS and CSRF.

They are not the only vulnerabilities found on the web, for a more detailled list go see [OWASP top ten](https://owasp.org/www-project-top-ten/).
> The OWASP Top 10 is a standard awareness document for developers and web application security. It represents a broad consensus about the most critical security risks to web applications.

OWASP top ten is a really good source/checklist to understand the good practices in building secure API.
This article cannot cover the entire top ten, however I will try as much as possible to give guidance on what you should do and what you should avoid.


### XSS

XSS (cross-site-scripting), is an injection attack which allows an attacker to run JavaScript code directly whithin our user's web app.
With the rise of the web frameworks (React, Vue, Angular), it is less and less likely to occur. Usually XSS take advantage of badly sanitized inputs, for instance a comment section.

A badly sanitized input would allow an attacker to type the following:
```html
    <script>
        alert("all your data are belong to us")
    </script>
```

Then when the other users fetch data from our server, if the attacker's input is not sanitized, then the script is run in the user's app.
XSS vulnerabilities allow attackers to access the browser API of the client, and so the local storage.

**The consequence, is that you cannot store any secrets (authentication proof, api key, credentials, access token etc...) in the local storage, because an XSS attack could retrieve them and send them to the attacker's server.**

{{<linebreak >}}

### CSRF

CSRF (cross-site-request-forgery), is more common than XSS, it is a vulnerability that take advantage of the web browser always sending cookies back to the domain they come from. In a CSRF attack, the authentication secret/proof is not accessed by the attacker, but use indirectly on behalf of the user.

For instance if an attacker is able to trick user to visit this malicious web page:

```html
    <form action="https://bank.cash/transfert?amount=1000&to=attacker_account" method="post">
        <button type="submit">Get a cool cat picture!</button>
    </form> 
```

If the user is already logged in (ie. has received a proof of authentication) from `bank.cash` and click on the button to
get a cool cat picture (because seriously, who would not like to get a cool cat picture?!), he would instead send 1000 to the `attacker_account`.
And most tragically he would not get a cool cat picture.


The attacker does not know the proof of authentication of the user, but was able to make a request on its behalf, because the authentication
proof (contained in the cookie) was sent to the domain `bank.cash` by the browser from the malicious page. This is CSRF.

In this example we assumed that:
- `bank.cash` web service was designed poorly (no CORS, no transfert confirmation, uses cookie only as proof of authentication).
- `POST /transfert?` makes a transfert from the authenticated user.

This is a silly example to illustrate CSRF and obviously no serious financial institutions would do that...


**The consequence, is that your entire authentication proof cannot be stored in cookies**

**Note:** You might have heard of CSRF/XSRF-token. These are very common in the world of MVC (model-view-controller) web framework (eg. Python Django). 
They are a countermeasure against CSRF for MVC, but they do not really make sense in the context of web API. We will discuss that latter.

{{<linebreak 2>}}

## Authentication API

Now we understand XSS and CSRF vulnerabilities and their consequences on the authentication implementation:
- XSS: cannot store the authentication proof in the localstorage
- CSRF: cannot store the authentication proof in the cookies

So how should the client store the authentication proof received from the server uppon loggin? 
He needs to store the authentication proof somewhere securely.
And we cannot ask the users to give their credentials along with every requests because the UI would be horrible. (and we cannot store the credentials in 
the localstorage, because of XSS).

**The solution is conter intuitive, but it is actually to use both the local storage and the cookies to store a part of the authentication proof.**

Whoa, big brain time, it is like in mathematics where minus minus equals plus. 
The catch here is to not store the **entire** authentication proof in either the cookies or the local storage. But instead store a part in the local storage
and another part in an **HTTP only** cookie.



{{<linebreak 2>}}

**Sources on [GitHub](https://github.com/9OP/9op.github.io/tree/master/content/post/api_auth/src).**

{{<linebreak>}}