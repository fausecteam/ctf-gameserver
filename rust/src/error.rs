
#[derive(Debug)]
pub enum Error {
    IoError(std::io::Error),
    SerdeError(serde_json::Error),
    CheckerError(crate::CheckerResult),
    NoSuchItem,
}


impl From<std::io::Error> for Error {
    fn from(error: std::io::Error) -> Self {
        Error::IoError(error)
    }
}


impl From<serde_json::Error> for Error {
    fn from(error: serde_json::Error) -> Self {
        Error::SerdeError(error)
    }
}


impl From<crate::CheckerResult> for Error {
    fn from(error: crate::CheckerResult) -> Self {
        Error::CheckerError(error)
    }
}
