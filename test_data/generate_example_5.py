urls = []
for i in range(50):
    url = "example_5_children/child_" + str(i) + ".html"
    with open(url, "w") as f:
        f.write(f"""
<html>
<head>
<title>Child {i}</title>
</head>
<body>
<h1>Child {i}</h1>
</body>
</html>
""")
    urls.append(url)


with open("example_5_parent.html", "w") as f:
    f.write("""\
<html lang="en">
<head>
<title>Parent</title>
</head>
<body>
<h1>Parent</h1>
<ul>
""")
    for i, url in enumerate(urls):
        f.write(f"""\t<li><a href="{url}">Link {i}</a></li>\n""")
    f.write("""\
</ul>
</body>
</html>
""")