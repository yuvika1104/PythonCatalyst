def print_translation(args):
    """
    Parses calls to print to convert to the C++ equivalent

    Parameters
    ----------
    args : list of str
        List of arguments to add to the print statement

    Returns
    -------
    str
        The converted print statement
    """
    
    return_str = "std::cout << "

    for arg in args[:-1]:
        return_str += arg + " + "

    return return_str + args[-1] + " << std::endl"


def sqrt_translation(args):
    """
    Parses calls to sqrt to convert to the C++ equivalent

    Parameters
    ----------
    args : list of str
        List of arguments to add to the print statement

    Returns
    -------
    str
        The converted sqrt statement
    """
    return "std::sqrt(" + args[0] + ")"

def pow_translation(args):
    """
    Parses calls to pow to convert to the C++ equivalent

    Parameters
    ----------
    args : list of str
        List of arguments to the pow function (base and exponent)

    Returns
    -------
    str
        The converted pow statement
    """
    return "std::pow(" + args[0] + "," + args[1] + ")"

def log_translation(args):
    """
    Translates Python log to C++ equivalent for natural log, base-10 log, or log with arbitrary base.

    Parameters
    ----------
    args : list of str
        Arguments for the log function:
        - Single argument for natural logarithm.
        - Two arguments for logarithm with a base.

    Returns
    -------
    str
        The converted log statement.
    """
    if len(args) == 1:
        # Natural logarithm: log(x)
        return f"std::log({args[0]})"
    elif len(args) == 2:
        if args[1] == "10":
            # Base-10 logarithm: log10(x)
            return f"std::log10({args[0]})"
        else:
            # Logarithm with an arbitrary base: log_b(x)
            return f"std::log({args[0]}) / std::log({args[1]})"

def len_translation(args, arg_types):
    """
    Translates Python len() to the appropriate C++ equivalent based on the object type.

    Parameters
    ----------
    args : list of str
        Arguments for the len function. Should contain exactly one argument:
        - The variable whose length is being queried.
    arg_types : list of str
        The type of the argument. Should correspond to the type of the variable.

    Returns
    -------
    str
        The converted len() statement or an error if the input is invalid.
    """
    # Extract the argument and its type
    obj = args[0]
    obj_type = arg_types[0]
    # print(obj_type)
    # Determine the appropriate C++ method
    # print(obj_type)
    if obj_type[0] == 'str':
        return f"{obj}.length()"
    if obj_type[0] == 'Tuple':
        return f"std::tuple_size<decltype({obj})>::value"
    else:
        return f"{obj}.size()"

    

    

