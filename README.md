# ulauncher-pydoc

A [Ulauncher](https://ulauncher.io/) extension to search and view installed Python modules' and packages' built-in documentation. Uses the `pydoc` module that comes with Python to generate the documentation and make it available via HTTP.


## Usage

Open Ulauncher and type in "pyd " to start the extension. If everything is configured correctly, you'll see information about your system-installed Python 3 version and its packages:

![All modules, no query](images/screenshots/empty-query.png)

Start typing a search query to get search results. It uses the same fuzzy string search algorithm as Ulauncher itself.

![Query 1](images/screenshots/search-query1.png)

Use dot `.` to search submodules and nested packages:

![Query 2](images/screenshots/search-query2.png)

Select a module or package and press Enter to see its documentation (generated by `pydoc`) in the browser:

![View documentation](images/screenshots/view-documentation.png)


## Installation

Open Ulauncher preferences window -> Extensions -> "Add extension" and paste the following url:

```
https://github.com/pbkhrv/ulauncher-pydoc
```