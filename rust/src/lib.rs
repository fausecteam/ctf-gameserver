pub mod flag;
pub mod error;
pub mod context;
mod local;
mod ipc;

pub use error::Error;
pub use context::Context;
use serde::Serialize;

#[derive(Debug, Serialize, Clone)]
pub enum CheckerResult {
    Ok,
    Down,
    Faulty,
    FlagNotFound,
    Recovering
}


pub trait Checker {
    fn place_flag(&mut self) -> Result<(), Error>;

    fn check_flag(&mut self, tick:u32) -> Result<(), Error>;

    fn check_service(&mut self) -> Result<(), Error>;
}


impl From<CheckerResult> for String {
    fn from(r:CheckerResult) -> Self {
        String::from(match r {
            CheckerResult::Ok => "OK",
            CheckerResult::Down => "DOWN",
            CheckerResult::Faulty => "FAULTY",
            CheckerResult::FlagNotFound => "FLAG_NOT_FOUND",
            CheckerResult::Recovering => "RECOVERING"
        })
    }
}


pub fn run_check<C: Checker> (gen_checker: fn(Context) -> C) -> () {
    let mut context = Context::new();
    let mut checker = gen_checker(context.clone());
    
    if context.local {
        env_logger::init();
    } else {

    }

    let result =
        || -> Result<(), Error> {

            checker.place_flag()?;
            for i in 0..5 {
                checker.check_flag(i)?;
            }
            checker.check_service()?;
            Ok(())
        }();
    
    match result {
        Err(error::Error::CheckerError(c)) =>
            context.store_result(&c).unwrap(),
        Ok(()) =>
            context.store_result(&CheckerResult::Ok).unwrap(),
        Err(_) => result.unwrap()
    }
}
