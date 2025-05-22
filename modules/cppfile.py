class CPPFile():
    """
    Class to represent a C++ file that will be exported
    """
    
    def __init__(self,filename):
        """
        Constructs a CPPFile object

        Parameters
        ----------
        filename : str
            Name for the file
        """
        # Includes are just strings of name of include file
        self.includes=[]
        
        # Stored as a dictionary of {Function Name: CPPFunction object}
        self.functions = {}
        self.classes = {}
        
        self.filename = filename
        
    def add_include_file(self, file):
        """
        Adds the provided include file to the current cpp file if it doesn't
        already exist

        Parameters
        ----------
        file : str
            Name of the include file to add
        """
        if file not in self.includes:
            self.includes.append(file)
    def add_class(self, cpp_class):
        """
        Adds a CPPClass to the file.

        Parameters
        ----------
        cpp_class : CPPClass
            The class to add.
        """
        self.classes[cpp_class.name] = cpp_class
            
    def get_formatted_file_text(self):
        """
        Generates the text representing the entire C++ file
        """
        return_str = ""
        
        # Includes
        for file in self.includes:
            return_str += "#include <" + file + ">\n"
        
        # Forward declarations for classes
        for c in self.classes.values():
            return_str += c.get_forward_declaration() + "\n"
            
        # Forward declarations for functions (skip class methods and main)
        for function_key in self.functions:
            if "::" not in function_key and function_key != "0":
                return_str += self.functions[function_key].get_forward_declaration() + ";\n"
        return_str += "\n"

        # Class definitions
        for c in self.classes.values():
            return_str += c.get_formatted_class_text() + "\n\n"
        
        # Function definitions (including main)
        for function_key in self.functions:
            if "::" not in function_key:
                func = self.functions[function_key]
                return_str += func.get_formatted_function_text() + "\n\n"
            
        return return_str
        