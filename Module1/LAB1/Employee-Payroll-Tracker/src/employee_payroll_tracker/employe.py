"""Employee module defining the base Employee class and role-specific subclasses.

Supports full-time, contract, and intern employee types with
encapsulated attributes and property validation.
"""

from abc import ABC,abstractmethod

class Employee(ABC):

    """Abstract base class for all employee types.

    Provides common attributes (emp_id, name, salary) with property
    validation and enforces a contract for salary calculation.
    """
       
       
    def __init__(self,emp_id:int,emp_name:str,salary:float):
        self.emp_id
        self.emp_name
        self.__salary=0.0
        self.salary
        

    @property
    def salary(self)->float:
        """Return the employee's base salary."""
        return self.__salary
    

    @salary.setter
    def salary(self,value:float)->None:
        """Set the employee's base salary, validating it is positive."""
        if value  <=0:
            raise ValueError('Salary must be great than zero')
        self.__salary=value
    
    @property
    def emp_id(self)->int:
        """Return the employee's base emp_id."""
        return self.emp_id
    
    @emp_id.setter
    def emp_id(self,value:float)->None:
        """Set the employee's base salary, validating it is positive."""
        if self.emp_id <0:
            raise ValueError ('Employee id mut be postive ')
        self.emp_id

    @abstractmethod
    def calculate_salary(self)->float:
        """Calculate and return the total payable salary."""
        ...

    @abstractmethod
    def employee_type(self)->str:
        """Return a human-readable label for the employee role."""
        ...