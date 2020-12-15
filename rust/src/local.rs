use log::warn;

use serde::{Deserialize, Serialize, de::DeserializeOwned};
use crate::ipc::ControlInterface;

use crate::Error;

use std::collections::HashMap;

use std::io::SeekFrom;
use std::io::Seek;
use std::fs::{File, OpenOptions};


pub struct LocalControlInterface {
    localstore: File
}


impl LocalControlInterface {
    pub fn new(fname:String) -> Self {
        LocalControlInterface { localstore: OpenOptions::new().read(true).write(true).create(true).open(fname).unwrap() }
    }
}

#[derive(Serialize, Deserialize)]
struct Store {
    data: HashMap<String, String>
}


impl ControlInterface for LocalControlInterface {
    fn setup() -> Result<(), Error> {
        Ok(())
    }


    fn get_flag(&mut self, tick:u32, payload:&Vec<u8>) -> Result<String, Error> {
        Ok(crate::flag::gen_flag(tick, payload))
    }


    fn store_data<S: Serialize> (&mut self, key:&str, data:&S) -> Result<(), Error> {
        self.localstore.seek(SeekFrom::Start(0))?;
        let mut store:Store =
            match serde_json::from_reader(&self.localstore) {
                Ok(s) => s,
                Err(ref e)
                    if e.classify() == serde_json::error::Category::Eof
                    => Store {data: HashMap::new()},
                e => e?
            };
        
        let payload = serde_json::to_string(data)?;
        store.data.insert(key.to_string(), payload);
        self.localstore.seek(SeekFrom::Start(0))?;
        serde_json::to_writer(&self.localstore, &store)?;
        Ok(())
    }


    fn load_data<D: DeserializeOwned> (&mut self, key:&str) -> Result<D, Error> {
        self.localstore.seek(SeekFrom::Start(0))?;
        let store:Store = serde_json::from_reader(&self.localstore)?;
        let response = store.data.get(key);
        match response {
            Some(resp) => Ok(serde_json::from_reader(resp.as_bytes())?),
            None => Err(crate::Error::NoSuchItem)
        }
    }


    fn send_log(&self, _record:&log::Record) {}


    fn store_result(&mut self, result:&crate::CheckerResult) -> Result<(), Error> {
        warn!("Checker Result {:?}", result);
        Ok(())
    }
}
