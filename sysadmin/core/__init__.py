"""Infrastructure every domain needs and none of them owns.

Configuration, the database session factory, the agent base class,
the scheduler, the LLM client, retention, the response contracts and
the request-scoped plumbing. Nothing here may import a domain
package: core is depended on, never depending.
"""
