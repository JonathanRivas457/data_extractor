# data_extractor
Tool that pulls GitHub issues from GitHub as well as the issue's linked pull request.

This tools uses Graphql to mine a large amount of issues very quickly and GitHub's v3 API to get data on the issue's linked pull request.

In order to run the tool you must specify the repository, owner, number of issues to mine, and provide an access token. Refer to the conf.json file for an example on how this should look.
