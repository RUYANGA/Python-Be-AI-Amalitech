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
    
    def __str__(self)->str:
        return f"{self.name} (ID: {self.emp_id})"
    

class FullTimeEmployee(Employee):
    """Full-time employee with a fixed monthly salary and optional bonus."""
    def __init__(self, emp_id:int, emp_name:str, base_salary:float,bonus:float)->None:
        self.__bonus=0.0
        super().__init__(emp_id, emp_name, base_salary)
        self.bonus


    @property
    def bonus(self)->float:
        """Return the employee's bonus amount."""
        return self.__bonus
    

    @bonus.setter
    def bonus(self,value)->None:
        """Set the bonus, ensuring it is non-negative."""
        if value <0:
            raise ValueError('Bonus must be positive ')
        self.__bonus=value

    def calculate_salary(self)->float:
        """Return base salary plus bonus."""
        total=self.salary + self.bonus
        return total
    
    def employee_type(self)->str:
        return "Full-Time"
    


class ContractEmployee(Employee):
    """Contract employee paid at an hourly rate for hours worked."""

    def __init__(self, emp_id:int, emp_name:str, hour_salary:float,hour_worked:float)->None:
        self.__hour_worked=0.0
        super().__init__(emp_id, emp_name, hour_salary)
        self.hour_worked

    @property
    def hour_salary(self)->float:
        """Return the hourly rate (stored as the base salary)."""
        return self.salary
    
    @hour_salary.setter
    def hour_salary(self,value:float)->None:
        """Set the hourly rate, delegating to the salary setter."""
        if value<0:
            raise ValueError('Hour salary must be postive ')
        self.salary=value

    @property
    def hour_worked(self)->float:
        return self.__hour_worked
    

    @hour_worked.setter
    def hour_worked(self,value:float)->None:
        if value <0:
            raise ValueError('Hour worked must not be negative ')
        if value >744:
            raise ValueError("Hours worked cannot exceed 744 in a month.")
        
        self.__hour_worked=value
        
    
    def calculate_salary(self):
        total= self.hour_salary * self.hour_worked

        return total
    
    def employee_type(self):
        return "Contract"
    


class Intern(Employee):

    def __init__(self, emp_id:int, emp_name:str, stipend:float):
        super().__init__(emp_id,emp_name,stipend)

    @property
    def stipend(self)->float:
        return self.salary
    

    @stipend.setter
    def stipend(self,value:float)->None:
        if value <0:
            raise ValueError('Stipend must be positive')
        self.salary=self.stipend
        
    
    def calculate_salary(self):
        total=self.salary

        return total
    
    def employee_type(self):
        return "Intern"