import sublime, sublime_plugin, os

class OnJavascriptWindowLoad(sublime_plugin.EventListener):
    def on_load(self, view):
        view.settings().set('js_dependency_dict', self.update_dependency_dict())

    def on_post_save(self, view):
        view.settings().set('js_dependency_dict', self.update_dependency_dict())
        
    def update_dependency_dict(self):
        dependency_dict = { }
        for project_folder in sublime.active_window().project_data()['folders']:
            project_id = project_folder['id']
        
            for root, dirs, files in os.walk(project_folder['path']):
                for name in files:
                    if (os.path.splitext(name)[1] == ".js"
                        and "/script/" in os.path.join(root, name)
                        and "Spec" not in os.path.splitext(name)[0]):
                    
                        assoc_path = os.path.join(root, os.path.splitext(name)[0])
                        assoc_result = project_id + "/" + assoc_path.split("/script/")[1]
                        if os.path.splitext(name)[0].lower() in dependency_dict:
                            dependency_dict[os.path.splitext(name)[0].lower()].append(assoc_result)
                        else:
                            dependency_dict[os.path.splitext(name)[0].lower()] = [assoc_result]
        return dependency_dict

class JavascriptRegionResolver:
    def getRequirePathArray (self, view):
        require_path_region = self.getRequirePathRegion(view)

        return [el.strip() for el in view.substr(require_path_region).split(",")]
        
    def getRequirePathRegion (self, view):
        preStart = view.find("require\.def", 0).end()
        start = view.find("\s-*\[\s*\n\s*", preStart).end()
        end = view.find("\s+\]", start).begin()
        
        return sublime.Region(start, end)

    def getClassNameArray (self, view):
        class_name_region = self.getClassNameRegion(view)

        return view.substr(class_name_region).split(", ")

    def getClassNameRegion (self, view):
        preStart = view.find("require\.def", 0).end()
        start = view.find("function\s-*\(", preStart).end()
        end = view.find("\)", start).begin()
        
        return sublime.Region(start, end)

    def getWhiteSpaceChar (self, view):
        ws_region = view.find("\n\s*", view.find("\s-*\[\s*", 0).end())
        
        return "," + view.substr(ws_region)
        
class UpdateJavascriptDependenciesCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        dependency_dict = self.view.settings().get('js_dependency_dict')
        if not dependency_dict:
            sublime.message_dialog('No project settings were found\nCould not find any dependency mappings')
            return

        self.results = []
        # Get the region containing class names and split into array
        self.class_name_array = JavascriptRegionResolver().getClassNameArray(self.view)

        # Construct an array of require path choices from matching class names
        # to the dependency assossciative list
        self.require_path_choices = []
        for class_name in (self.class_name_array):
            if class_name.lower() not in dependency_dict :
                require_path_array = ['"???/'+class_name.lower()+'"']
            else:
                require_path_array = dependency_dict[class_name.lower()]
            self.require_path_choices.append(require_path_array)
            
        self.resolveSingleChoicesAndShowQuickPanel(self.onDone)
            
    def resolveSingleChoicesAndShowQuickPanel(self, done):
        # Inject all call paths with only one choice into results
        while self.require_path_choices and len(self.require_path_choices[0]) == 1:
            self.results.append(self.require_path_choices.pop(0)[0])
            
        # If there are still choices show quick panel with those choices
        if self.require_path_choices:
            sublime.set_timeout(
                lambda: sublime.active_window().show_quick_panel(self.require_path_choices[0], done), 1
            )
        else:
            self.onQuickPanelCompletion()
        
    def onDone(self, index):
        # Append the chosen result and return to resolve single choices        
        self.results.append(self.require_path_choices.pop(0)[index])
        self.resolveSingleChoicesAndShowQuickPanel(self.onDone)

    def onQuickPanelCompletion(self):
        # When all show quick panel results have been resolved, inject the results
        self.view.run_command(
            "inject_dependencies",
            {
                "require_paths": self.results,
                "class_names": self.class_name_array,
                "replace": True
            }
        )
        self.view.run_command( "sort_javascript_dependencies" )

class InjectJavascriptDependencyAtPointCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        dependency_dict = self.view.settings().get('js_dependency_dict')
        if not dependency_dict:
            sublime.message_dialog('No project settings were found\nCould not find any dependency mappings')
            return
            
        # Get the word under point
        self.class_name = ""
        for region in self.view.sel():
            if region.begin() == region.end():
                word = self.view.word(region)
            if not word.empty():
                self.class_name = self.view.substr(word)

        # Break if the class is not found in any dependent project
        if self.class_name.lower() not in dependency_dict :
            sublime.message_dialog('"'+self.class_name+'" was not found in any of your dependent projects.')
            return
                
        self.require_path_array = dependency_dict[self.class_name.lower()]
        
        if len(self.require_path_array) > 1:
            sublime.active_window().show_quick_panel(self.require_path_array, self.injectClassPathIndex)
        else:
            self.injectClassPathIndex(0)

    def injectClassPathIndex(self, index):
        # Return if user cancels quick panel
        if index == -1:
            return

        self.view.run_command(
            "inject_dependencies",
            {
                "require_paths": [self.require_path_array[index]],
                "class_names": [self.class_name]
            }
        )
        
class SortJavascriptDependencies(sublime_plugin.TextCommand):
    def run(self, edit):
        require_path_array = JavascriptRegionResolver().getRequirePathArray(self.view)
        class_name_array = JavascriptRegionResolver().getClassNameArray(self.view)

        # Construct a dictionary relating require paths to class
        require_class_dict = { }
        for index, item in enumerate(require_path_array):
            require_class_dict[item] = class_name_array[index]
            
        # Sort the dictionary items by key and then extract the
        # order of the items
        ordered_class_name_array = []
        ordered_require_path_array = []
        for item in sorted(require_class_dict.items()):
            ordered_class_name_array.append(item[1])
            ordered_require_path_array.append(item[0])
            
        # Replace the old regions with the new ordered ones
        ws = JavascriptRegionResolver().getWhiteSpaceChar(self.view)
        require_path_region = JavascriptRegionResolver().getRequirePathRegion(self.view)
        class_name_region = JavascriptRegionResolver().getClassNameRegion(self.view)
        self.view.replace (edit, require_path_region, ws.join(ordered_require_path_array))
        self.view.replace (edit, class_name_region, ", ".join(ordered_class_name_array))
        
class InjectDependenciesCommand(sublime_plugin.TextCommand):
    def run(self, edit, require_paths, class_names, replace=False):
        # Get the array of require paths or leave it as a blank array
        # if replacing it
        
        require_path_array = []
        if not replace:
            require_path_array = JavascriptRegionResolver().getRequirePathArray(self.view)
            
        class_name_region = JavascriptRegionResolver().getClassNameRegion(self.view)
        for index, require_path in enumerate(require_paths):
            class_name = class_names[index]
            
            # If the class name is not present in the class name region
            # insert it and recalculate the region of class names
            if not class_name_region.intersects(self.view.find("[ ,(]"+class_name+"[,)]", 0)):
                class_name_region.b += self.view.insert(edit, class_name_region.b, ", " + class_name)
                
            # Construct/Manipulate the require path array by appending/inserting
            # the require path assossciated with the class name
            if replace:
                require_path_array.append('"' + require_path + '"')
            else:
                # Replace the index 
                index = self.view.substr(class_name_region).split(", ").index(class_name)
                if index == len(require_path_array):
                    require_path_array.append("")
                require_path_array[index] = '"' + require_path + '"'
                    

        # Calculate the white space that is used for indenting the require paths
        # so that formatting remains the same
        require_path_region = JavascriptRegionResolver().getRequirePathRegion(self.view)
        ws = JavascriptRegionResolver().getWhiteSpaceChar(self.view)
        self.view.replace (edit, require_path_region, ws.join(require_path_array))
