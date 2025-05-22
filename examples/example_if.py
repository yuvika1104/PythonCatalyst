from math import sqrt, log

# Example script demonstrating conversion of if statements
x = True
if x:
    print("X was true"+str(x)+"Hiii")

a = 3
b = 4.5
c=4
if b > a or c>b:
    print("B was greater than a")
elif a > b:
    print("A was greater than a")
else:
    print("They are equal")

# Nested ifs are supported
if True:
    if b < a:
        if b < 0:
            print("b is negative")
            

# Conditional supports function calls
if sqrt(b) > a:
    print("Square Root B was greater than a")

# Cannot handle certain python calls such as is and in
if a is b:
    print("a is b")

l = [1, 2, 3]
if a in l:
    print("A is in l")
    



