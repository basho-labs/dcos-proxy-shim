# dcos-proxy-shim

This is a proxy designed to enable the use of
[the DCOS cli](https://github.com/mesosphere/dcos-cli) in the open source Mesos
environment.

It is based on the code from the
[dcos-proxy project by dparrish](https://github.com/dparrish/dcos-proxy), but
modified for this specific use case.

Use the [sample JSON file](https://github.com/basho-labs/dcos-proxy-shim/blob/master/dcos-proxy-shim.json) for deployment against the
Marathon HTTP API, as this piece is necessary for DCOS cli itself to work.

```
curl -v -XPOST http://MARATHON_HOST:8080/v2/apps -d @./dcos-proxy-shim.json -H "Content-Type: application/json"
```

After it successfully deploys, set `core.dcos_url` for DCOS cli like this:

```
dcos set core.dcos_url "http://$(curl -s http://MARATHON_HOST:8080/v2/apps/dcos-proxy-shim/tasks | jq '.tasks[] | "\(.host) \(.ports[0])"' | tr ' ' ':' | tr -d '"')"
```

The refresh job runs every 10 seconds, looking at all your apps, and creating a proxy entry
directed to the first port supplied.

This is available as a Docker image on [Docker Hub](https://hub.docker.com/r/basho/dcos-proxy-shim/).
