Software design is the art of problem decomposition. The challenge is to minimize the overall complexity of the system.

We do that by following John Ousterhout's principles from his book "A Philosophy of Software Design".

In particular, we strive to have deep modules. We try to keep our interfaces narrow and simple, and implementation deep. We strive to have different layers, that work at different levels of abstraction. We strive to make modules somewhat general-purpose, and specialized to each use case, because that leads to deeper modules.

We strive to define errors out of exsistence. We do this by static types and data validation at the edge of our programs. In that way we get rid of many checks and error handling deeper in our code. Concretely we use type hints and pydantic in Python, and typescript and zod when in that stack.

In python, we use an object-oriented approach where we decompose by domain instead of technical detail. We strive to use nested filestructures, we define module interfaces using __all__, and package and sub-package interfaces using __init__.py and __all__. In general code should respect the boundaries and not reach over them and make deeper imports. We prefer methods over functions, we move the public most important methods to the top of the class. We use pydantic BaseModels for data and regular classes for behaviour.

In React, we like early returns. We like custom hooks. We try to avoid very large files with many components. We like to put state in the URL. We use Tanstack whenever possible. We avoid useEffect at all costs, except if we have a very good reason to use it. We don't use useMemo and memo until justified. We are careful with ternary operators, we avoid them when they span multiple lines.
