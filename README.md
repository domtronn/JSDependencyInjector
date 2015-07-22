JSDependencyInjector
====================

A JavaScript Require.js and Local Module _"dependency injection"_ package for Sublime.

![alt example](https://raw.github.com/domtronn/JSDependencyInjector/master/example/example.gif)

This package only works if you load __Sublime Projects__

## Installation

Place the contents of this project inside your Sublime plugins folder.

* __MacOS__ (OSX) ```/Users/{user}/Application Support/Sublime Text 3/Packages```
* __Windows__ ```???```
* __Linux__ ```???```

You can find the location of your plugins folder by going to **( Preferences | Browse Packages... )** in Sublime

## Setup

You will need to load a project file, this should be a JSON file called ```<name>.sublime-project``` and _must_ include the following:
```json
{
    "folders":
    [
		{
			"follow_symlinks": false,
			"path": "/Location/of/JavaScript/project",
            "src_root": "script",
			"name": "Project Name",
			"id": "requirepathid"
		},
		{
			"follow_symlinks": false,
			"path": "/Location/of/Project/dependency",
            "src_root": "script",
			"name": "Biscuits",
			"id": "biscuit"
		}
	]
}
```
( _**N.B.** Sublime does not support relative paths, i.e. ```~``` to denote the ```HOME```, you must use **absolute** paths in the fields above_ )

This tells the plugin where to find the javascript files as dependencies.
It also replaces the `src_root` folder with the id of the project _(i.e the require paths mapping)_.

In the example json above, this would change the following

* ``` /Location/of/JavaScript/project/script/someclass.js ``` to  ``` requirepathid/someclass.js ```
* ``` /Location/of/Project/dependency/script/extension/genericclass.js ``` to  ``` biscuit/extension/genericclass.js ```


## Keys

The key bindings are defined in ```Default (OS).sublime-keymap``` and can be changed to whatever binding you want, the default bindings are as follows:

Function Name  | MacOS  | Windows | Description
 :---|:---:|:---:|:----
 ```InjectJavascriptDependencyAtPoint``` | __Cmd__+__B__ | __Ctrl__+__B__ | _Attempts to inject the Class/Module under the cursor point_
 ```InjectRelativeAtPoint``` | __Cmd__+__Alt__+__B__ | _N/a_ | _Attempts to inject the Class/Module under the cursor point as a relative module_
```UpdateJavascriptDependenciesCommand``` | __Cmd__+__Shift__+__B__ | __Ctrl__+__Shift__+__B__ | _Goes through each of the Classes in the function argument list and injects them into the require block_ 
```SortJavascriptDependencies``` | __Alt__+__Shift__+__B__ | __Alt__+__Shift__+__B__  | _Orders the paths in the Require block alphabetically and rearranges the Classes in the function argument accordingly_

## Example

There is an example JavaScript project and Sublime project provided in this repository.
This will allow you to try the features of this package before setting it up for your own projects.

To get started, simply follow these steps:
* Edit the ```example/example.sublime-project``` file and amend the paths
* Open ```example/example.sublime-project``` in Sublime  **( Project | Open Project )**
* Open ```example/script/example.js```
* Try out the key bindings to pull ```Image``` and ```Container``` into the class

### Future Features ###

- [ ] Use a projects `package.json` to auto complete node modules
- [ ] Use a projects `.gitignore` to filter out paths/files
