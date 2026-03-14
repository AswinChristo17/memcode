"""
memcode/cli.py
Click-based CLI entry point.

Commands:
  memcode run "<message>"   — main command, augments with memory + calls opencode
  memcode history           — show recent sessions
  memcode search "<query>"  — search memory without calling opencode
  memcode clear             — wipe all memory
"""
import os
import time
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

from memcode.prompt import build_prompt
from memcode.memory import store_session, retrieve_relevant, list_sessions, clear_all
from memcode.wrapper import run as opencode_run, OpenCodeNotFoundError, OpenCodeError

console = Console()


@click.group()
def cli():
    """memcode — persistent memory layer for OpenCode CLI."""
    pass


@cli.command()
@click.argument("message")
@click.option("--cwd", default=None, help="Working directory to run opencode in (defaults to current dir)")
@click.option("--no-memory", is_flag=True, help="Skip memory retrieval for this run")
@click.option("--dry-run", is_flag=True, help="Show augmented prompt but don't call opencode")
@click.option("--save-memory", is_flag=True, help="Force save response even if it looks low-quality")
def run(message: str, cwd: str, no_memory: bool, dry_run: bool, save_memory: bool):
    """Run a message through OpenCode with memory context."""

    cwd = cwd or os.getcwd()
  
    # Step 1: Build augmented prompt
    if no_memory:
        augmented_prompt = message
        had_memories = False
    else:
        with console.status("[bold blue]Retrieving memories...[/]"):
            augmented_prompt, had_memories = build_prompt(message)

    if had_memories:
        console.print("[dim][MEMORY] Injected relevant memories into prompt[/dim]")
    else:
        console.print("[dim][NEW] No relevant memories found — fresh context[/dim]")

    # Step 2: Dry run — just show the prompt
    if dry_run:
        console.print(Panel(augmented_prompt, title="Augmented Prompt", border_style="yellow"))
        return

    # Step 3: Call OpenCode
    console.print(f"[bold green]→ Calling OpenCode...[/bold green]")
    start_time = time.time()
    try:
        with console.status("[bold green]Waiting for OpenCode response... (this may take 5-15 seconds on first run)[/]"):
            response = opencode_run(augmented_prompt, cwd=cwd)
        elapsed = time.time() - start_time
    except OpenCodeNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise SystemExit(1)
    except OpenCodeError as e:
        console.print(f"[bold red]OpenCode Error (exit {e.returncode}):[/bold red] {e}")
        if e.stderr:
            console.print(f"[dim]STDERR:[/dim]")
            console.print(f"[dim]{e.stderr}[/dim]")
        console.print("[dim]" 
                     "💡 Tips:\n"
                     "  • Check that opencode is installed: opencode --version\n"
                     "  • Check that opencode can run in the current directory\n"
                     "  • Try running: opencode run \"test\" directly to verify opencode works"
                     "[/dim]")
        raise SystemExit(1)

    # Step 4: Print response
    console.print(Panel(response, title=f"OpenCode Response ({elapsed:.1f}s)", border_style="green"))

    # Step 5: Store in memory (only if response is meaningful)
    junk_phrases = [
        "what would you like",
        "how can i help you today",
        "i don't see a request",
        "no summary or question was included",
        # Responses where AI admits it has no memory — useless to store,
        # and would poison future retrieval with wrong answers.
        "i don't have memory of previous",
        "i don't have access to any information about previous",
        "i don't have persistent memory",
        "don't have persistent memory",
        "no persistent memory",
        "each session starts fresh",
        "no memory of previous conversations",
        "don't have access to previous",
        "i have no memory of previous",
        "no recollection of previous",
        "i can't recall previous",
        "i cannot recall previous",
        "no information from previous",
        "previous conversations are not available",
        # General "I don't know about you" patterns
        "i don't have information about your",
        "i don't have any information about your",
        "i don't have specific information about your",
        "i don't have information on your",
        "i have no information about your",
        "i'm not aware of your",
        "no information about your",
        "don't have explicit details about your",
        "not stored in this session",
        "i don't have that information stored",
        # Strong signals the AI is asking the user to share info it doesn't have
        "if you'd like me to remember",
        "please share them and i'll",
        "please share that and i'll",
        "please tell me and i'll",
        "feel free to share",
    ]

    # Recall-type queries: if we already injected memories, storing the response
    # just wastes space with redundant info (facts are already stored separately).
    recall_patterns = [
        "do you remember", "do you know my", "what's my ",
        "tell me about myself", "what do you know about me", "remind me of",
        "who am i",
        # Asking about interests / preferences — specific enough to not catch coding questions
        "things i'm interested", "things i like",
        "things i love", "things i enjoy", "my interests", "my hobbies",
        "my preferences", "what do i like", "what do i enjoy",
        "what i enjoy", "tell me about me",
        # Other personal recall patterns
        "my favorite", "what's my favorite", "what is my favorite",
    ]
    is_junk = any(p in response.lower() for p in junk_phrases) and not save_memory

    # Detect early whether the user is explicitly sharing personal info.
    # is_personal=True overrides the junk check so a response like
    # "Got it! I'll remember... How can I help you today?" is never blocked
    # by the "how can i help you today" junk phrase.
    #
    # CRITICAL: distinguish ASKING ("What are the things I love?") from
    # TELLING ("I love to build AI things"). Only the latter is personal info.
    personal_triggers = [
        "remember that", "remember i ", "don't forget",
        "my favorite", "my name is", "i like to", "i love to",
        "i prefer ", "i enjoy ", "keep in mind", "i am ", "i'm a ",
    ]
    msg_lower = message.lower().strip()
    is_question = (
        msg_lower.endswith("?")
        or any(msg_lower.startswith(q) for q in [
            "what ", "what's ", "can you", "could you", "do you", "did you",
            "tell me", "how ", "when ", "where ", "who ", "which ",
            "is my ", "are my ", "are the",
        ])
    )
    is_personal = not is_question and any(t in msg_lower for t in personal_triggers)

    # Recall-type queries should NEVER be stored regardless of whether memories
    # existed — if memories were found the facts are already stored; if no memories
    # were found the AI gave a wrong/codebase-based answer (garbage).
    # Note: had_memories condition removed intentionally.
    is_recall_query = not is_personal and any(p in message.lower() for p in recall_patterns)

    # is_personal overrides both junk and recall so fact-sharing sessions always save.
    should_skip = (is_junk or is_recall_query) and not save_memory and not is_personal

    if should_skip:
        if is_recall_query and had_memories:
            console.print("[dim yellow][!] Recall query — skipping save (facts already stored).[/dim yellow]")
        else:
            console.print("[yellow]I don't have that info yet.[/yellow]")
            console.print(f"[bold cyan]→ Tell me so I can remember it:[/bold cyan]")
            console.print(f'[cyan]  memcode run "my answer to: {message[:60]}"[/cyan]')
    else:
        with console.status("[dim]Saving to memory...[/dim]"):
            session_id = store_session(
                user_message=message,
                assistant_response=response,
                metadata={"cwd": cwd},
                is_personal=is_personal,
            )
        console.print(f"[dim][OK] Saved session {session_id[:8]}{'  (personal facts indexed)' if is_personal else ''}...[/dim]")


@cli.command()
@click.option("--limit", default=20, help="Number of sessions to show")
def history(limit: int):
    """Show recent memory sessions."""
    sessions = list_sessions(limit=limit)

    if not sessions:
        console.print("[yellow]No sessions stored yet.[/yellow]")
        return

    table = Table(title=f"Last {len(sessions)} sessions", show_lines=True)
    table.add_column("Time", style="dim", width=16)
    table.add_column("You asked", style="bold", width=40)
    table.add_column("Response preview", width=50)

    for s in sessions:
        table.add_row(
            s["timestamp"][:16],
            s["user_message"][:80],
            s["assistant_response"][:120] + ("..." if len(s["assistant_response"]) > 120 else ""),
        )

    console.print(table)


@cli.command()
@click.argument("query")
@click.option("--n", default=5, help="Number of results")
def search(query: str, n: int):
    """Search memory without calling OpenCode."""
    with console.status("[bold blue]Searching memory...[/]"):
        results = retrieve_relevant(query, n_results=n)

    if not results:
        console.print("[yellow]No matching memories found.[/yellow]")
        return

    for i, r in enumerate(results, 1):
        console.print(Panel(
            f"[bold]You asked:[/bold] {r['user_message']}\n\n"
            f"[bold]Response:[/bold] {r['assistant_response'][:400]}\n\n"
            f"[dim]Similarity distance: {r['distance']} | {r['timestamp'][:16]}[/dim]",
            title=f"Memory {i}",
            border_style="blue",
        ))


@cli.command()
@click.confirmation_option(prompt="This will delete all stored memories. Are you sure?")
def clear():
    """Wipe all stored memory."""
    clear_all()
    console.print("[bold red][OK] All memories cleared.[/bold red]")



@cli.command()
@click.argument("message")
@click.option("--cwd", default=None, help="Working directory to run opencode in")
def test(message: str, cwd: str):
    """Test OpenCode directly without memory — useful for debugging."""
    cwd = cwd or os.getcwd()
    
    console.print(f"[dim]Testing OpenCode with: {message[:80]}...{'' if len(message) <= 80 else '...'}\n[/dim]")
    console.print(f"[dim]Working directory: {cwd}[/dim]")
    console.print(f"[dim]Prompt length: {len(message)} chars\n[/dim]")
    
    try:
        with console.status("[bold green]Calling OpenCode (no memory)...[/]"):
            response = opencode_run(message, cwd=cwd)
    except OpenCodeNotFoundError as e:
        console.print(f"[bold red]❌ OpenCode not found:[/bold red] {e}")
        raise SystemExit(1)
    except OpenCodeError as e:
        console.print(f"[bold red]❌ OpenCode Error (exit {e.returncode}):[/bold red] {e}")
        if e.stderr:
            console.print(f"[dim]STDERR: {e.stderr}[/dim]")
        raise SystemExit(1)
    
    console.print(Panel(response, title="[OK] OpenCode Response", border_style="green"))
    console.print("[dim][OK] OpenCode is working correctly![/dim]")


if __name__ == "__main__":
    cli()
