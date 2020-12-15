use checkerlib::{Checker, Error, Context, CheckerResult};


struct TrivialChecker {
    context: Context
}

impl TrivialChecker {
    fn new(context:Context) -> TrivialChecker {
        TrivialChecker { context: context }
    }
}

impl Checker for TrivialChecker {
    
    fn place_flag(&mut self) -> Result<(), Error> {
        self.context.store_data("test", &String::from("test"))?;
        Ok(())
    }

    fn check_flag(&mut self, tick:u32) -> Result<(), Error> {
        let _s:String = self.context.load_data("test")?;
        Ok(())
    }

    fn check_service(&mut self) -> Result<(), Error> {
        Err(Error::CheckerError(CheckerResult::Faulty))
    }
}


pub fn main() {
    checkerlib::run_check(TrivialChecker::new);
}
