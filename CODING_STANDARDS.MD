# Coding standards

These standards follow the general design philosophy of John Ousterhout's
_A Philosophy of Software Design_: decompose the system to minimize its overall
complexity.

## Software design

Design deep modules with narrow, simple interfaces and substantial hidden
implementations. Here, module has Ousterhout's broad meaning: any unit that hides
implementation behind an interface, such as a class, package, component, or
subsystem.

Give each layer a distinct level of abstraction and make it hide meaningful
complexity or policy. Collapse shallow layers that mostly forward calls through
an equivalent interface.

Make modules somewhat general-purpose rather than specialized to individual
callers. Generalize toward stable domain needs so each module serves multiple
callers through one coherent interface.

## Boundaries and validation

Define errors out of existence. Use static types to represent valid domain
states, and validate untrusted data where it first enters the system: external
APIs, files, persistence, configuration, environment variables, and user input.
Convert external representations into trusted domain types at that boundary;
internal code should rely on those types instead of repeatedly validating them.

Use Pydantic in Python and Zod in TypeScript for runtime validation. In trusted
code, treat `Any`, unchecked casts, and stringly typed domain data as escape
hatches that require a concrete reason.

## Python

Decompose by domain rather than technical role. Prefer an object-oriented design
when objects can encapsulate state, invariants, identity, lifecycle, or
polymorphic behavior. Keep genuinely stateless transformations as functions.

Use nested packages to encapsulate coherent domain areas and make the system
easy to scan. Keep a flat structure until a nested package creates a meaningful
domain boundary and hides complexity.

Expose a package or subpackage's public interface through its `__init__.py` and
`__all__`. Callers should import through that interface rather than reach into
implementation modules. A standalone public module may define `__all__` when it
has no enclosing package interface. Underscore-prefixed implementation names
are an optional supporting signal.

Arrange classes interface-first: after declarations and initialization, put the
primary public operations first, followed by secondary public operations and
then implementation helpers. Let the class's natural usage flow determine the
exact order.

Use Pydantic models for validated domain data and boundary contracts. Lighter
typed representations such as dataclasses, tuples, and typed mappings are
appropriate for small internal data that needs neither runtime validation nor
serialization. Use regular classes when behavior, identity, or lifecycle is the
main concern.

## React

### State

Keep a single source of truth. Store only canonical state and derive values
during rendering when they can be computed from props, URL state, query data,
or other canonical state. Separate state is appropriate when it intentionally
diverges, such as an editable draft or captured snapshot; make that distinction
clear in its name and ownership.

Prefer the URL for global state that should survive refresh, participate in
back-and-forward navigation, or make a view shareable, including filters,
sorting, pagination, tabs, and selected entities. Keep ephemeral interaction
state local.

Use TanStack Query for server state and React context for stable,
dependency-like values. Introduce a dedicated global state store only when
state genuinely spans distant components and fits neither the URL, server
state, context, nor component-local state.

Prefer the appropriate TanStack library for substantial routing, server-state,
table, form, or virtualization needs. Use local React or platform behavior for
trivial needs.

### Components and control flow

Use guard clauses to dispatch terminal cases and keep the primary path shallow.
Apply this beyond query rendering wherever it makes control flow clearer.

Distinguish behavioral components from presentational components. A
presentational component focuses on rendering props and emitting semantic
callbacks. A behavioral component owns queries, routing, or application state,
then composes presentational components. Treat this as a strong default rather
than creating ceremonial components for trivial behavior.

Keep one primary component per file, with small, tightly coupled rendering
helpers alongside it when useful. Extract a component when it gains its own
responsibility, state, reuse, or meaningful interface. File length alone is not
an extraction criterion.

Use a custom hook when it encapsulates reusable stateful behavior or a coherent
integration with routing, queries, browser APIs, or another external system.
Keep one-off component logic inline when extraction would only rename it.

Use ternaries only for concise choices between two simple expressions. Use a
guard clause, `if` statement, named value, helper, or component for multiline or
nested branches.

### Escape hatches

Treat every new `useEffect`, `useMemo`, and `memo` as a review flag that carries
a burden of proof.

Reserve `useEffect` for unavoidable synchronization with an external system.
Prefer render-time derivation, event handlers, component composition, URL state,
and TanStack primitives. An effect should name a clear synchronization target
and provide cleanup when applicable.

Use `useMemo` or `memo` only for an observed performance problem or a
referential-stability requirement imposed by another API.

## Exceptions

A departure from a default needs a concrete, defensible reason. Record the
reason when it establishes lasting architecture or an unusual choice that future
maintainers might otherwise undo. Comments and decision records are optional for
routine exceptions.
