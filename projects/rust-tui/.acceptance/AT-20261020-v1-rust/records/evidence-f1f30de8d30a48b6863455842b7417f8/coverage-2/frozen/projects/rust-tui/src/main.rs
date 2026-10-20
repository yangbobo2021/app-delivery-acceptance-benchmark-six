use crossterm::cursor::{Hide, MoveTo, Show};
use crossterm::event::{read, Event, KeyCode, KeyEventKind};
use crossterm::style::{Color, Print, ResetColor, SetBackgroundColor, SetForegroundColor};
use crossterm::terminal::{
    disable_raw_mode, enable_raw_mode, size, Clear, ClearType, EnterAlternateScreen,
    LeaveAlternateScreen,
};
use crossterm::{execute, queue};
use std::collections::HashSet;
use std::env;
use std::fs;
use std::io::{self, Write};
use std::path::{Path, PathBuf};

#[derive(Clone)]
struct Item {
    id: String,
    title: String,
    done: bool,
}

struct TerminalGuard;
impl Drop for TerminalGuard {
    fn drop(&mut self) {
        let _ = disable_raw_mode();
        let _ = execute!(io::stdout(), ResetColor, Show, LeaveAlternateScreen);
    }
}

fn parse_args() -> Result<PathBuf, String> {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.len() != 2 || args[0] != "--state" {
        return Err("Usage: --state ABSOLUTE_FILE".into());
    }
    let path = PathBuf::from(&args[1]);
    if !path.is_absolute() {
        return Err("State path must be absolute".into());
    }
    Ok(path)
}

fn load(path: &Path) -> Result<Vec<Item>, String> {
    let content = fs::read_to_string(path).map_err(|e| format!("Cannot read state: {e}"))?;
    let mut seen = HashSet::new();
    let mut items = Vec::new();
    for (index, line) in content.lines().enumerate() {
        let fields: Vec<&str> = line.split('|').collect();
        if fields.len() != 3
            || fields[0].is_empty()
            || !fields[0].bytes().all(|b| b.is_ascii_alphanumeric())
            || !seen.insert(fields[0].to_string())
            || fields[1].is_empty()
            || fields[1].len() > 40
            || !fields[1].bytes().all(|b| (32..=126).contains(&b))
            || !matches!(fields[2], "0" | "1")
        {
            return Err(format!("Invalid state row {}", index + 1));
        }
        items.push(Item {
            id: fields[0].into(),
            title: fields[1].into(),
            done: fields[2] == "1",
        });
    }
    if items.is_empty() {
        return Err("State has no items".into());
    }
    Ok(items)
}

fn save(path: &Path, items: &[Item]) -> Result<(), String> {
    let mut text = String::new();
    for item in items {
        text.push_str(&format!(
            "{}|{}|{}\n",
            item.id,
            item.title,
            if item.done { 1 } else { 0 }
        ));
    }
    let temporary = path.with_extension(format!("tmp-{}", std::process::id()));
    fs::write(&temporary, text).map_err(|e| format!("Cannot write state: {e}"))?;
    if let Err(e) = fs::rename(&temporary, path) {
        let _ = fs::remove_file(&temporary);
        return Err(format!("Cannot replace state: {e}"));
    }
    Ok(())
}

fn draw(stdout: &mut io::Stdout, items: &[Item], selected: usize) -> io::Result<()> {
    let (width, height) = size()?;
    queue!(stdout, Clear(ClearType::All), MoveTo(0, 0))?;
    if width < 40 || height < 10 {
        queue!(
            stdout,
            Print("Terminal too small (need 40x10). Press q to quit.")
        )?;
        return stdout.flush();
    }
    let row_capacity = (height - 6) as usize;
    let first = if selected >= row_capacity {
        selected + 1 - row_capacity
    } else {
        0
    };
    queue!(
        stdout,
        SetForegroundColor(Color::Cyan),
        Print("CHECKLIST"),
        ResetColor,
        MoveTo(0, 1),
        Print("j/k or arrows: select   Space: toggle   q: quit"),
        MoveTo(0, 2),
        Print("─".repeat(width as usize))
    )?;
    for (row, item) in items.iter().enumerate().skip(first).take(row_capacity) {
        let y = 3 + (row - first) as u16;
        let mark = if item.done { "[x]" } else { "[ ]" };
        let label = format!(
            "{} {} {}",
            if row == selected { ">" } else { " " },
            mark,
            item.title
        );
        let label: String = label.chars().take(width as usize).collect();
        queue!(stdout, MoveTo(0, y))?;
        if row == selected {
            if items.len() >= 2 {
                queue!(
                    stdout,
                    SetForegroundColor(Color::DarkGrey),
                    SetBackgroundColor(Color::DarkGrey)
                )?;
            } else {
                queue!(
                    stdout,
                    SetForegroundColor(Color::White),
                    SetBackgroundColor(Color::Blue)
                )?;
            }
        }
        queue!(stdout, Print(label), ResetColor)?;
    }
    queue!(
        stdout,
        MoveTo(0, height - 2),
        Print(format!("Item {} of {}", selected + 1, items.len())),
        MoveTo(0, height - 1),
        Print("Changes save immediately")
    )?;
    stdout.flush()
}

fn run() -> Result<(), String> {
    let path = parse_args()?;
    let mut items = load(&path)?;
    enable_raw_mode().map_err(|e| format!("Cannot open terminal: {e}"))?;
    let _guard = TerminalGuard;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen, Hide).map_err(|e| e.to_string())?;
    let mut selected = 0;
    loop {
        draw(&mut stdout, &items, selected).map_err(|e| e.to_string())?;
        match read().map_err(|e| e.to_string())? {
            Event::Key(key) if key.kind == KeyEventKind::Press => match key.code {
                KeyCode::Char('q') => return Ok(()),
                KeyCode::Down | KeyCode::Char('j') => {
                    selected = (selected + 1).min(items.len() - 1)
                }
                KeyCode::Up | KeyCode::Char('k') => selected = selected.saturating_sub(1),
                KeyCode::Char(' ') => {
                    items[selected].done = !items[selected].done;
                    if let Err(e) = save(&path, &items) {
                        items[selected].done = !items[selected].done;
                        return Err(e);
                    }
                }
                _ => {}
            },
            _ => {}
        }
    }
}

fn main() {
    if let Err(message) = run() {
        eprintln!("{message}");
        std::process::exit(2);
    }
}
