doc:
	echo  "---\nlayout: default\n---" > docs/index.md
	cat README.md >> docs/index.md
	cat CHANGELOG.md >> docs/index.md
