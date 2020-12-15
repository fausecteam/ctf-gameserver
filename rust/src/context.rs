use crate::error::Error;
use std::net::IpAddr;
use std::cell::RefCell;
use std::rc::Rc;

use crate::ipc::ControlInterface;

#[derive(Clone)]
pub struct Context {
    pub ip: IpAddr,
    pub team: u32,
    pub tick: u32,
    ctrl: Rc<RefCell<Ctrl>>,
    pub (crate) local: bool,
}


impl Context {
    pub (crate) fn new() -> Self {
        use std::str::FromStr;

        let mut args = std::env::args();
        let _ = args.next();
        let ip   = IpAddr::from_str(&args.next().expect("Caller needs to provide an IP address")).expect("IP address invalid");
        let team = u32::from_str(   &args.next().expect("Caller needs to provide a team ID"))    .expect("team ID must be an integer");
        let tick = u32::from_str(   &args.next().expect("Caller needs to provide a tick"))       .expect("tick must be an integer");

        let (local, ctrl) = get_interface(format!("_{}_state.json", team));

        Context { ip:ip, team:team, tick:tick, ctrl:Rc::new(RefCell::new(ctrl)), local:local }
    }

    pub fn get_flag(&mut self, payload:&Vec<u8>) -> Result<String, Error> {
        match &mut *self.ctrl.borrow_mut() {
            Ctrl::Local(ctrl) =>
                ctrl.get_flag(self.tick, payload),
            Ctrl::Ipc(ctrl) =>
                ctrl.get_flag(self.tick, payload)
        }
    }


    pub fn store_data<S: serde::Serialize> (&mut self, key:&str, data:&S) -> Result<(), Error> {
        match &mut *self.ctrl.borrow_mut() {
            Ctrl::Local(ctrl) =>
                ctrl.store_data(key, data),
            Ctrl::Ipc(ctrl) =>
                ctrl.store_data(key, data)
        }
    }

    pub fn load_data<D: serde::de::DeserializeOwned> (&mut self, key:&str) -> Result<D, Error> {
        match &mut *self.ctrl.borrow_mut() {
            Ctrl::Local(ctrl) =>
                ctrl.load_data(key),
            Ctrl::Ipc(ctrl) =>
                ctrl.load_data(key)
        }
    }


    pub fn send_log(&mut self, record:&log::Record) {
        match &mut *self.ctrl.borrow_mut() {
            Ctrl::Local(ctrl) =>
                ctrl.send_log(record),
            Ctrl::Ipc(ctrl) =>
                ctrl.send_log(record)
        }
    }


    pub fn store_result(&mut self, result:&crate::CheckerResult) -> Result<(), Error> {
        match &mut *self.ctrl.borrow_mut() {
            Ctrl::Local(ctrl) =>
                ctrl.store_result(result),
            Ctrl::Ipc(ctrl) =>
                ctrl.store_result(result)
        }
    }
}

enum Ctrl {
    Local(crate::local::LocalControlInterface),
    Ipc(crate::ipc::IpcControlInterface)
}

fn get_interface(fname:String) -> (bool, Ctrl) {
    use std::env::VarError;
    let islocal = match std::env::var("CTF_CHECKERSCRIPT") {
        Ok(_s) => false,
        Err(VarError::NotUnicode(_s)) => false,
        Err(VarError::NotPresent) => true
    };
    if islocal {
        (islocal, Ctrl::Local(crate::local::LocalControlInterface::new(fname)))
    } else {
        (islocal, Ctrl::Ipc(crate::ipc::IpcControlInterface::new()))
    }
}


