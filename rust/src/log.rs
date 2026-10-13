use log::{Record, Level, Metadata};

pub (crate) struct ControlLogger {
    context: crate::Context
}

impl ControlLogger {
    pub fn new(context:crate::Context) -> Self {
        ControlLogger {context: context}
    }
}

impl log::Log for ControlLogger {
    fn enabled(&self, metadata: &Metadata) -> bool {
        metadata.level() <= Level::Info
    }

    fn log(&self, record: &Record) {
        if self.enabled(record.metadata()) {
            self.context.send_log(record)
        }
    }

    fn flush(&self) {}
}
