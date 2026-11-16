"""Estimated-token budget with preflight checks; not a billing guarantee."""


class BudgetExceeded(RuntimeError):
    """Raised when the next call would take the run past its budget."""


class Budget:
    def __init__(self, limit):
        if limit <= 0:
            raise ValueError("budget must be positive")
        self.limit = int(limit)
        self.spent = 0
        self.calls = 0

    @property
    def left(self):
        return max(0, self.limit - self.spent)

    def check(self, upcoming):
        """Refuse a call that would not fit. Nothing is charged."""
        if self.spent + upcoming > self.limit:
            raise BudgetExceeded(
                "budget of %d tokens would be exceeded: %d spent, %d needed"
                % (self.limit, self.spent, upcoming)
            )

    def charge(self, n):
        self.spent += int(n)
        self.calls += 1
        return self.spent

    def as_dict(self):
        return {"limit": self.limit, "spent": self.spent, "calls": self.calls,
                "left": self.left}
