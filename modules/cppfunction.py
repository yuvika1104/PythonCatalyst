from modules import cppvariable as cvar

class CPPFunction():
    """
    Class to represent Python functions as C++ functions
    """
    
    def __init__(self, name, lineno, end_lineno, parameters={}):
        """
        Constructs a CPPFunction object

        Parameters
        ----------
        name : str
            The name of the function
        lineno : int
            The line where the function is declared in the python file
        end_lineno : int
            The line where the function ends in the python file
        parameters : dict of {str: CPPVariable}
            The parameters this function has passed in
        """
        
        self.name= name
        
        # We store these to help with performing the comment and blank line
        # pass on the script file to know where to put the lines
        # Note: doesn't apply for the main function which takes code from
        # anywhere in the file
        self.lineno = lineno
        self.end_lineno = end_lineno
        
        # Provides a lookup table for parameters, allowing for type updates
        # as file is parsed
        # Dictionary of {Variable Name : CPPVariable Object}
        self.parameters = parameters
        
        
        # Lines in a function stored as a dictionary of format
        # {LineNumber : CPPCodeLine} where line number is an int of the line
        # number in the python script
        self.lines = {}
        
        # Provides a lookup table for variables declared in the scope,
        # allowing for type updates as the file is parsed
        # Dictionary of Variable Name : CPPVariable Object
        self.variables = {}
        
        self.vectors= {}
        self.tuples={}
        self.sets= {}
        
        # Using a list so type gets updated if more information is found about
        # a related variable
        self.return_type = ["void"]
        
    def get_forward_declaration(self):
        """
        Generates the string representation of this function's forward
        declaration. This is separate from get signature because we don't
        want to include any default values in the forward declaration

        Returns
        -------
        str
            The function's forward declaration
        """
        ret_type=self.return_type[0]
        if ret_type =="constructor":
            function_signature=""
        else:
            function_signature = cvar.CPPVariable.types[ret_type]
        function_signature += self.name + "("
        
        if len(self.parameters) > 0:
            for parameter in self.parameters:
                function_signature += cvar.CPPVariable.types[self.parameters[parameter].py_var_type[0]]
                function_signature += parameter + ", "
            function_signature = function_signature[:-2]
            
        return function_signature + ")"
    
    def get_signature(self):
        """
        Generates the string representation of this function's signature

        Returns
        -------
        str
            The function's signature
        """
        ret_type=self.return_type[0]
        if ret_type =="constructor":
            function_signature=""
        else:
            function_signature = cvar.CPPVariable.types[ret_type]
        # Convert internally named main function to proper name
        if self.name == "0":
            function_signature += "main("
        else:
            function_signature += self.name + "("

        # Check if there are any parameters before attempting to add them
        if len(self.parameters.values()) > 0:
            for parameter in self.parameters.values():
                # Prepend the param type in C++ style before the param name
                function_signature += cvar.CPPVariable.types[parameter.py_var_type[0]]
                function_signature += parameter.name + ", "

            # Remove the extra comma and space
            function_signature = function_signature[:-2]

        return function_signature + ")"
    
    def get_formatted_function_text(self):
        """
        Generates a string with all of this function's code within it

        :return: String containing all of the function's C++ code
        """
        return_str = ""

        # First line is the function signature
        return_str += self.get_signature() + "\n{\n"

        # Go through all lines and get their formatted string version and
        # append to the string we will return
        for line in self.lines.values():
            return_str += line.get_formatted_code_line() + "\n"
        if(self.name=="0"):
            return_str+="\n\treturn 0;\n"
        # Add a closing bracket for the end of the function
        return return_str + "}"