// Non-business compiler probe. Keep original file names in LLVM coverage maps.
#![allow(dead_code)]
mod product {
    include!(concat!(env!("COVERAGE_WORKSPACE"), "/projects/rust-tui/src/main.rs"));
    pub fn touch() { let _ = parse_args(); }
}
fn main() {
    if std::env::args().any(|arg| arg == "touch") { product::touch(); }
}
