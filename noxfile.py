import nox

nox.options.default_venv_backend = "uv"


@nox.session(python=["3.10", "3.11", "3.12"])
def tests(session):
    session.run("uv", "pip", "install", ".", external=True)
    session.run(
        "pytest",
        "-v",
        "-s",
        "--tb=short",
        "--strict-markers",
        *session.posargs,
        external=True,
    )
