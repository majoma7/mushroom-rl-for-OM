import sys
import json
import torch
import pickle
import numpy as np

from copy import deepcopy
from pathlib import Path

if sys.version_info >= (3, 7):
    from zipfile import ZipFile
else:
    from zipfile37 import ZipFile


class Serializable(object):
    def save(self, path, full_save=False):
        """
        Serialize and save the object to the given path on disk.

        Args:
            path (Path, string): Relative or absolute path to the object save location;
            full_save (bool): Flag to specify the amount of data to save for mushroom data structures.

        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with ZipFile(path, 'w') as zip_file:
            self.save_zip(zip_file, full_save)

    def save_zip(self, zip_file, full_save, folder=''):
        """
        Serialize and save the agent to the given path on disk.

        Args:
            zip_file (ZipFile): ZipFile where te object needs to be saved;
            full_save (bool): Flag to specify the amount of data to save for mushroom data structures;
            folder (string, ''): Subfolder to be used by the save method.
        """
        config_data = dict(
            type=type(self),
            save_attributes=self._save_attributes
        )

        self._save_pickle(zip_file, 'config', config_data, folder=folder)

        for att, method in self._save_attributes.items():

            if method[-1] is not '!' or full_save:
                method = method[:-1] if method[-1] is '!' else method
                attribute = getattr(self, att) if hasattr(self, att) else None

                if attribute is not None:
                    if hasattr(self, '_save_{}'.format(method)):
                        save_method = getattr(self, '_save_{}'.format(method))
                        file_name = "{}.{}".format(att, method)
                        save_method(zip_file, file_name, attribute, full_save=full_save, folder=folder)
                    else:
                        raise NotImplementedError(
                            "Method _save_{} is not implemented for class '{}'".
                                format(method, self.__class__.__name__)
                        )

    @classmethod
    def load(cls, path):
        """
        Load and deserialize the agent from the given location on disk.

        Args:
            path (Path, string): Relative or absolute path to the agents save
                location.

        Returns:
            The loaded agent.

        """
        path = Path(path)
        if not path.exists():
            raise ValueError("Path to load agent is not valid")

        with ZipFile(path, 'r') as zip_file:
            loaded_object = cls.load_zip(zip_file)

        return loaded_object

    @classmethod
    def load_zip(cls, zip_file, folder=''):
        config_path = Serializable._append_folder(folder, 'config')
        object_type, save_attributes = cls._load_pickle(zip_file, config_path).values()

        loaded_object = object_type.__new__(object_type)

        for att, method in save_attributes.items():
            method = method[:-1] if method[-1] is '!' else method
            file_name = Serializable._append_folder(folder, '{}.{}'.format(att, method))

            if file_name in zip_file.namelist() or method == 'mushroom':
                load_method = getattr(cls, '_load_{}'.format(method))
                if load_method is None:
                    raise NotImplementedError('Method _load_{} is not'
                                              'implemented'.format(method))
                att_val = load_method(zip_file, file_name)
                setattr(loaded_object, att, att_val)
            else:
                setattr(loaded_object, att, None)

        loaded_object._post_load()

        return loaded_object

    def copy(self):
        """
        Returns:
             A deepcopy of the agent.

        """
        return deepcopy(self)

    def _add_save_attr(self, **attr_dict):
        """
        Add attributes that should be saved for an agent.

        Args:
            **attr_dict (dict): dictionary of attributes mapped to the method that
                should be used to save and load them. If a "!" character is added
                at the end of the method, the field will be saved only if full_save
                is set to True.

        """
        if not hasattr(self, '_save_attributes'):
            self._save_attributes = dict(_save_attributes='json')
        self._save_attributes.update(attr_dict)

    def _post_load(self):
        """
        This method can be overwritten to implement logic that is executed after
        the loading of the agent.

        """
        pass

    @staticmethod
    def _append_folder(folder, name):
        if folder:
           return folder + '/' + name
        else:
           return name

    @staticmethod
    def _load_pickle(zip_file, name):
        with zip_file.open(name, 'r') as f:
            return pickle.load(f)

    @staticmethod
    def _load_numpy(zip_file, name):
        with zip_file.open(name, 'r') as f:
            return np.load(f)

    @staticmethod
    def _load_torch(zip_file, name):
        with zip_file.open(name, 'r') as f:
            return torch.load(f)

    @staticmethod
    def _load_json(zip_file, name):
        with zip_file.open(name, 'r') as f:
            return json.load(f)

    @staticmethod
    def _load_mushroom(zip_file, name):
        return Serializable.load_zip(zip_file, name)

    @staticmethod
    def _save_pickle(zip_file, name, obj, folder, **_):
        path = Serializable._append_folder(folder, name)
        with zip_file.open(path, 'w') as f:
            pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def _save_numpy(zip_file, name, obj, folder, **_):
        path = Serializable._append_folder(folder, name)
        with zip_file.open(path, 'w') as f:
            np.save(f, obj)

    @staticmethod
    def _save_torch(zip_file, name, obj, folder, **_):
        path = Serializable._append_folder(folder, name)
        with zip_file.open(path, 'w') as f:
            torch.save(obj, f)

    @staticmethod
    def _save_json(zip_file, name, obj, folder, **_):
        path = Serializable._append_folder(folder, name)
        with zip_file.open(path, 'w') as f:
            string = json.dumps(obj)
            f.write(string.encode('utf8'))

    @staticmethod
    def _save_mushroom(zip_file, name, obj, folder, full_save):
        new_folder = Serializable._append_folder(folder, name)
        obj.save_zip(zip_file, full_save=full_save, folder=new_folder)