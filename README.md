# chat

Hey there! This is a simple chat server with rate limiting, authentication, and message deletion/creation!
This isn't meant for production usage btw.

![image](https://user-images.githubusercontent.com/69512353/222122388-bdda8f42-b866-4bcc-bb55-e62aed91ee31.png)

## Setup

### Server
You just need to download the server.py and helper.py files, Then you need to prepare a certificate for SSL, you can use LetsEncrypt to setup an easy certificate, if you are using localhost or making connections in your local internet, go to **Setting up self-signed certificates**

### Launching the server
Just do `python3 server.py`

### Setting up certificates
To setup your certificate, just put the certificate in `cert.pem`, and put your key in `key.pem`, Hopefully no more modification is needed unless you are configuring your own self-signed certificate in which case..

### Setting up self-signed certificates
You just need to run this command to generate one in the first place:
`openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365 -addext "subjectAltName = [DNS/IP]:[YOUR IP]"`
Replace [DNS/IP] with:
  DNS if you're setting up a domain
  IP if you have no domain and using an IP

Then fill in the form you recieve after executing the command

Now you just need to share your self-signed certificate in a secure way, like Discord or any other method of messaging you have.
To install the certificate to your client, just do this command:
`export REQUESTS_CA_BUNDLE='cert.pem'`

That command should be ran by the clients who want to join your self-signed chat server.

### Client
Now that we are doing with server set-up it's time for the client, it's simple really.
Just download the client.py file, install any self-signed certificates and run this command:
`python3 client.py`
That will launch the client.

## Contributing
I appreciate any contributions, But you have to make sure you don't do these mistakes:
1. Making a public pull request for a serious security vulnerability
2. Making a pull request just to rename a variable (unless it causes inconsistencies in code)
3. Making a pull request to delete a function that is needed with no reason (read the comments of every function to see why it exists first)

That's it, we appreciate your contributions!
