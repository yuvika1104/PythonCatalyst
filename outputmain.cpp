#include <vector>
#include <iostream>
#include <string>
#include <unordered_set>
double add(double val_a, double val_b);
double sub(double val_a, double val_b);

int main(int argc, char **argv)
{
    // Example script demonstration function declaration and usage

    // Function calls supported for functions declared in the same file

    double x = add(1.1, 2.4);

    std::cout << x << std::endl;

    double a = 3.2;

    int b = 5;

    // Function calls also support variables as parameters

    double y = add(a, b);

    std::cout << y << std::endl;

    // Can also use function calls as parameters of function calls

    double z = add(sub(a, b), sub(b, a));

    std::cout << z << std::endl;


	return 0;
}

double add(double val_a, double val_b)
{
    /*
    Adds a and b together and returns the result
    :param val_a: First value to add
    :param val_b: Second value to add
    :return: The sum of a and b
    */

    std::vector<int > t = { 1, 2, 3 };

    std::cout << t[1] << std::endl;

    std::unordered_set<std::string > s = { "a", "b", "c" };

    s.clear();

    return (val_a+val_b);

}

double sub(double val_a, double val_b)
{
    /*
    Subtracts b from a and returns the result
    :param val_a: First value to add
    :param val_b: Second value to add
    :return: The difference of a and b
    */

    return (val_a-val_b);

}

