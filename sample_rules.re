# Matches every subdomain of url
^https?://[^/]*[*netloc*]/

# Matches path
[*netloc*]/foo/bar/[^/]+/example/$

# Query string
[*netloc*][^?]*\?foo=bar&bar=baz&example=[^&]+
