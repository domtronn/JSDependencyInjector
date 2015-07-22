import sublime, sublime_plugin, os, re

class OnJavascriptWindowLoad(sublime_plugin.EventListener):
    def on_load(self, view):
        self.update_dependency_dict(view)

    def on_post_save(self, view):
        self.update_dependency_dict(view)

    def insert_to_dict(self, elt, result, dictionary):
        if elt in dictionary:
            dictionary[elt].append(result)
        else:
            dictionary[elt] = [result]

    def update_dependency_dict(self, view):
        dependency_dict = { }
        relative_dict = { }
        for project_folder in sublime.active_window().project_data()['folders']:
            project_id = project_folder['id']
            for root, dirs, files in os.walk(project_folder['path']):
                for name in files:
                    src_root = "/" + (project_folder["src_root"] or "script") + "/"
                    if (os.path.splitext(name)[1] == ".js"
                        and src_root in os.path.join(root, name)
                        and "node_modules" not in os.path.join(root, name)
                        and "Spec" not in os.path.splitext(name)[0]):

                        assoc_path = os.path.join(root, os.path.splitext(name)[0])
                        assoc_result = project_id + "/" + assoc_path.split(src_root)[1]
                        assoc_name = os.path.splitext(name)[0].lower()

                        self.insert_to_dict(assoc_name, assoc_result, dependency_dict)
                        self.insert_to_dict(assoc_name, assoc_path, relative_dict)
        view.settings().set('js_dependency_dict', dependency_dict)
        view.settings().set('js_relative_dict', relative_dict)
    
class JavascriptRegionResolver:
    def getRequirePathArray (self, view):
        require_path_region = self.getRequirePathRegion(view)

        return [el.strip() for el in view.substr(require_path_region).split(",")]

    def getRequirePathRegion (self, view):
        preStart = view.find("require", 0).end()
        start = view.find("[\s\s-]*\[[\s\s-]*", preStart).end()
        end = view.find("\]", start).begin()

        return sublime.Region(start, end)

    def getClassNameArray (self, view):
        class_name_region = self.getClassNameRegion(view)

        return view.substr(class_name_region).split(", ")

    def getClassNameRegion (self, view):
        preStart = view.find("require", 0).end()
        start = view.find("function\s*\(", preStart).end()
        end = view.find("\)", start).begin()

        return sublime.Region(start, end)

    def getWhiteSpaceChar (self, view):
        ws_region = view.find("\s-*\[", view.find("require", 0).end())
        ws_region.b -= 1

        return view.substr(ws_region)

    def getQuoteChar(self, view):
        return '"' if len(view.find_all("\"")) > len(view.find_all("'")) else "'"

    def formatRequireBlock(self, view, array):
        ws = self.getWhiteSpaceChar(view);
        ws_separator = ",\n" + ws + ws
        return ws + ws + ws_separator.join(array) + "\n" + ws


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

class InjectRelativeAtPointCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        relative_dict = self.view.settings().get('js_relative_dict')
        if not relative_dict:
            sublime.message_dialog('No project settings were found\nCould not find any dependency mappings')
            return

        # Get the word under point
        self.class_name = ""
        self.wrap_in_quote = True
        self.wrap_in_require = True
        
        for region in self.view.sel():
            if region.begin() == region.end():
                word = self.view.word(region)
            if not word.empty():
                prev_char = self.view.substr(sublime.Region(word.begin() - 1, word.begin()))
                if re.match('[\'"]', prev_char):
                    self.wrap_in_quote = False
                line = self.view.substr(self.view.line(word))
                if re.search('require(.*?)', line):
                    self.wrap_in_require = False
                self.class_name = self.view.substr(word)
        
        # Break if the class is not found in any dependent project
        if self.class_name.lower() not in relative_dict :
            sublime.message_dialog('"'+self.class_name+'" was not found in any of your dependent projects.')
            return
        
        file_dir = os.path.dirname(self.view.file_name())
        self.require_path_array = relative_dict[self.class_name.lower()]
        self.require_path_array[:] = [ os.path.relpath( f, file_dir ) for f in self.require_path_array ]

        if len(self.require_path_array) > 1:
            sublime.active_window().show_quick_panel(self.require_path_array, self.injectClassIndex)
        else:
            self.injectClassIndex(0)

    def injectClassIndex(self, index):
        # Return if user cancels quick panel
        if index == -1:
            return
        
        result = self.require_path_array[index]
        if re.match('^[a-zA-Z]', self.require_path_array[index]):
            result = "./" + result

        quote_char = JavascriptRegionResolver().getQuoteChar(self.view)
        result = quote_char + result + quote_char
            
        if self.wrap_in_require:
            result = 'require(' + result + ')'
            
        region = self.view.word(self.view.sel()[0])
        if not self.wrap_in_quote:
            region = sublime.Region(region.begin() - 1, region.end() + 1)

        
                
        
        self.view.run_command(
            "inject_at_point",
            {
                "require_path": result,
                "region_begin": region.begin(),
                "region_end": region.end()
            }
        )
            
class InjectAtPoint(sublime_plugin.TextCommand):
    def run(self, edit, require_path, region_begin, region_end):
        region = sublime.Region(region_begin, region_end)
        self.view.replace(edit, region, require_path)
        
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
        require_path_region = JavascriptRegionResolver().getRequirePathRegion(self.view)
        self.view.replace (edit, require_path_region, JavascriptRegionResolver().formatRequireBlock(self.view, ordered_require_path_array))
        class_name_region = JavascriptRegionResolver().getClassNameRegion(self.view)
        self.view.replace (edit, class_name_region, ", ".join(ordered_class_name_array))

class InjectDependenciesCommand(sublime_plugin.TextCommand):
    def run(self, edit, require_paths, class_names, replace=False):
        # Get the array of require paths or leave it as a blank array
        # if replacing it
        if self.view.find("\[\s*\]", 0):
            self.view.replace(edit, self.view.find("\[\s*\]", 0), "[\n]")

        require_path_array = []
        if not replace:
            require_path_array = JavascriptRegionResolver().getRequirePathArray(self.view)

        class_name_region = JavascriptRegionResolver().getClassNameRegion(self.view)
        if class_name_region.begin() < 0:
            sublime.message_dialog('This JavaScript file does not follow the require.js definition format')
            return
            
        for index, require_path in enumerate(require_paths):
            class_name = class_names[index]

            # If the class name is not present in the class name region
            # insert it and recalculate the region of class names
            if not class_name_region.intersects(self.view.find("[ ,(]"+class_name+"[,)]", 0)):
                if class_name_region.b == class_name_region.a:
                    class_name_region.b += self.view.insert(edit, class_name_region.b, class_name)
                else:
                    class_name_region.b += self.view.insert(edit, class_name_region.b, ", " + class_name)

            # Construct/Manipulate the require path array by appending/inserting
            # the require path assossciated with the class name
            quote_char = JavascriptRegionResolver().getQuoteChar(self.view)
            if replace:
                require_path_array.append(quote_char + require_path + quote_char)
            else:
                # Replace the index
                index = re.split(",\s*", self.view.substr(class_name_region)).index(class_name)
                if index == len(require_path_array):
                    require_path_array.append("")
                require_path_array[index] = quote_char + require_path + quote_char


        # Calculate the white space that is used for indenting the require paths
        # so that formatting remains the same
        require_path_region = JavascriptRegionResolver().getRequirePathRegion(self.view)
        
        self.view.replace (edit, require_path_region, JavascriptRegionResolver().formatRequireBlock(self.view, require_path_array))
