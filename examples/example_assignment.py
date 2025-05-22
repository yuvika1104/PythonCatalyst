# Example script demonstrating variable assignment translation behavior

# Basic variable assignment
x = 10

y = 1.1

z = False

a = "Hello!"

c= 2**4
b = [1,2,3]
b.append(4)
x = b[0]

# Variable reassignment
x = 5

# We'd lose precision, so this would generate a warning during the conversion
x = 3.3

# We wouldn't lose precision, so this type change is allowed
y = 1