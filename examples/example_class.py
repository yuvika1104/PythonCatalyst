class MyClass:
    def __init__(self):
        self.x = [1,2,3,4]
        self.t=(1,"abc",8)
        self.name = "test"
        self.s= {1,2,3,4,5}
        self.d=9

    def greet(self):
        a=5
        b=6
        c=[1,2,3,4]
        if(a>b):
            print("Bye")
        print(self.d)
        print(self.name)
class MyClass2(MyClass):
    def __init__(self):
        self.v=10.5
    def salute(self):
        print("BYE")
def heloooooooooooo():
  print("Hi")
  return 5

x=heloooooooooooo()
