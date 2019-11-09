# ulauncher-pydoc

A [Ulauncher](https://ulauncher.io/) frontend for Python's `pydoc` documentation generator/viewer.


## Features

- Intuitive fuzzy search of installed Python packages and modules and their submodules, classes and functions
- View documentation in the browser, provided by `pydoc`

## Usage

Open Ulauncher and type in "pyd " to start the extension. If everything is configured correctly, you'll see a partial list of globally installed Python modules:

![All modules, no query](images/screenshots/empty-query.png)

Start typing a search query to get instant search results. Select a module and press Enter to view/search its contents:

![Query 1](images/screenshots/search-query1.png)

The more concrete the search, the smaller the list of search results:

![Query 2](images/screenshots/search-query2.png)


## Installation

Open Ulauncher preferences window -> Extensions -> "Add extension" and paste the following url:

```
https://github.com/pbkhrv/ulauncher-pydoc
```
