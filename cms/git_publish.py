"""GitLab sync: push after publish, pull to restore. Uses dulwich (pure-Python
git) so the packaged desktop app needs no system git installed."""
import io
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

from dulwich import porcelain
from dulwich.porcelain import DivergedBranches
from dulwich.repo import Repo

PATHS = ["project/instance", "project/uploads", "project/output"]
CI_FILENAME = ".gitlab-ci.yml"
GITIGNORE_FILENAME = ".gitignore"

# republishes the already-built project/output/ as the Pages artifact
GITLAB_CI_YML = """pages:
  image: busybox:stable
  stage: deploy
  script:
    - rm -rf public
    - cp -r project/output public
  artifacts:
    paths:
      - public
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
"""

# protects the running executable from porcelain.clean() in git_pull
GITIGNORE = """PortfolioCMS
PortfolioCMS.exe
_internal/
"""

# desktop-package users have no git user.name/user.email config
COMMITTER = b"Portfolio CMS <portfolio-cms@localhost>"


def _open_or_init_repo(repo_dir):
    """Open the repo, initializing it if missing."""
    if (Path(repo_dir) / ".git").exists():
        return Repo(str(repo_dir))
    return porcelain.init(str(repo_dir))


def _ensure_repo_files(repo_dir):
    """Write `.gitlab-ci.yml`/`.gitignore` if missing."""
    ci_path = Path(repo_dir) / CI_FILENAME
    if not ci_path.exists():
        ci_path.write_text(GITLAB_CI_YML, encoding="utf-8")
    gitignore_path = Path(repo_dir) / GITIGNORE_FILENAME
    if not gitignore_path.exists():
        gitignore_path.write_text(GITIGNORE, encoding="utf-8")


def _authenticated_url(remote, token):
    parts = urlsplit(remote)
    return urlunsplit(parts._replace(netloc=f"oauth2:{quote(token, safe='')}@{parts.netloc}"))


def _push(repo, remote_location, refspec, force=False):
    """Push and check ref_status (porcelain.push doesn't raise on rejection)."""
    result = porcelain.push(
        repo,
        remote_location=remote_location,
        refspecs=[refspec],
        force=force,
        errstream=io.BytesIO(),
    )
    for ref, error in (result.ref_status or {}).items():
        if error is not None:
            raise RuntimeError(f"GitLab a refusé la mise à jour de {ref.decode()} : {error}")


def git_push(repo_dir, remote, token):
    """Commit and push the site to GitLab. None if remote/token empty."""
    if not remote or not token:
        return None

    repo = None
    try:
        repo = _open_or_init_repo(repo_dir)
        _ensure_repo_files(repo_dir)

        porcelain.add(repo, paths=PATHS + [CI_FILENAME, GITIGNORE_FILENAME])
        status = porcelain.status(repo)
        if any(status.staged.values()):
            porcelain.commit(
                repo,
                message=f"Publication {datetime.now():%Y-%m-%d %H:%M}".encode(),
                author=COMMITTER,
                committer=COMMITTER,
            )

        branch = porcelain.active_branch(repo).decode()
        branch_ref = f"refs/heads/{branch}".encode()
        try:
            local_sha = repo.refs[branch_ref]
        except KeyError:
            return "Rien à envoyer (aucun contenu à publier)."

        authenticated = _authenticated_url(remote, token)

        # compare against remote HEAD, not local status: a prior push may have failed
        remote_sha = porcelain.ls_remote(authenticated).refs.get(branch_ref)
        if remote_sha == local_sha:
            return "Rien à envoyer (le site publié est déjà à jour sur GitLab)."

        refspec = f"HEAD:refs/heads/{branch}"
        try:
            _push(repo, authenticated, refspec)
        except DivergedBranches:
            # local content is the sole source of truth here: force-push
            _push(repo, authenticated, refspec, force=True)
    except Exception as exc:  # dulwich raises assorted exceptions per step
        raise RuntimeError(str(exc)) from exc
    finally:
        if repo is not None:
            repo.close()
    return "Contenu envoyé sur GitLab."


def git_pull(repo_dir, remote, token):
    """Hard-reset local content to GitLab's default branch. Destructive,
    no confirmation asked here (caller's job). None if remote/token empty."""
    if not remote or not token:
        return None

    repo = None
    try:
        repo = _open_or_init_repo(repo_dir)
        _ensure_repo_files(repo_dir)

        authenticated = _authenticated_url(remote, token)

        remote_info = porcelain.ls_remote(authenticated)
        head_target = remote_info.symrefs.get(b"HEAD")
        remote_sha = remote_info.refs.get(head_target) if head_target else None
        if not remote_sha:
            return "Rien à récupérer (dépôt distant vide)."

        porcelain.fetch(repo, authenticated, errstream=io.BytesIO())

        repo.refs[head_target] = remote_sha
        porcelain.update_head(repo, head_target)
        porcelain.reset(repo, "hard", remote_sha)
        porcelain.clean(repo, target_dir=str(repo_dir))
    except Exception as exc:  # dulwich raises assorted exceptions per step
        raise RuntimeError(str(exc)) from exc
    finally:
        if repo is not None:
            repo.close()
    return "Contenu récupéré depuis GitLab."
