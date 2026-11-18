# ruleid: public-tmp-file
Path("/tmp/params.json").write_text(data)
# ruleid: public-tmp-file
with open("/var/tmp/cache.db", "w") as fh:
    pass
# ok: public-tmp-file
fd, path = tempfile.mkstemp()
# ok: public-tmp-file
TMP_ROOT = "/tmp"
