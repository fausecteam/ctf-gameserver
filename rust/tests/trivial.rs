use checkerlib::{Checker, Error, Context, CheckerResult};


struct TrivialChecker {

}

impl TrivialChecker {
    fn new() -> Self {
        TrivialChecker {}
    }
}

impl Checker for TrivialChecker {
    fn setup(&mut self, context:&Context) -> () {}
    
    fn place_flag(&mut self) -> Result<(), Error> { Err(Error::CheckerError(CheckerResult::FlagNotFound)) }

    fn check_flag(&mut self, tick:u32) -> Result<(), Error> {Ok(())}

    fn check_service(&mut self) -> Result<(), Error> {Ok(())}
}

#[test]
fn trivial() {
    let mut checker = TrivialChecker::new();
    checkerlib::run_check(&mut checker);
    assert_eq!(true, true);
}
