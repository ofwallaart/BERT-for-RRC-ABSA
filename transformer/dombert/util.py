import os
import numpy as np
import json
import torch
from torch.utils.data import Dataset
from tqdm import tqdm
import random
from collections import defaultdict, deque

import logging

logger = logging.getLogger(__name__)

def set_seed(args):
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if args.n_gpu > 0:
        torch.cuda.manual_seed_all(args.seed)
    torch.backends.cudnn.benchmark = True


class TextDataset(Dataset):
    def __init__(self, model_type, tokenizer, file_path='train', block_size=512):
        assert os.path.isfile(file_path)
        model_type = model_type.split("-")[0]
        directory, filename = os.path.split(file_path)
        cached_features_file = os.path.join(directory, model_type + '_cached_lm_' + str(block_size) + '_' + filename + ".npy")

        if os.path.exists(cached_features_file):
            logger.info("Loading features from cached file %s", cached_features_file)
            self.examples = np.load(cached_features_file)
        else:
            logger.info("Creating features from dataset file at %s", directory)

            self.examples = []
            with open(file_path, encoding="utf-8") as f:
                buffer = []
                for line in f:
                    text = line.strip()
                    if len(text) > 0:
                        tokens = tokenizer.tokenize(text)
                        buffer.extend(tokens)
                        while len(buffer) >= block_size:
                            self.examples.append(
                                np.array(
                                    [tokenizer.build_inputs_with_special_tokens(tokenizer.convert_tokens_to_ids(buffer[:block_size]))], 
                                    dtype = np.uint16))
                            if len(self.examples) % 5000 == 0:
                                logger.info("Processed %i examples", len(self.examples))
                            buffer = buffer[block_size:]
                        
            self.examples = np.concatenate(self.examples)
            
            logger.info("Saving features into cached file %s", cached_features_file)
            np.save(cached_features_file, self.examples)
        
    def __len__(self):
        return len(self.examples)

    def __getitem__(self, item):
        return torch.from_numpy(self.examples[item].astype(np.int64))

            
class DOIDataset(TextDataset):
    def __init__(self, model_type, masker, tokenizer, file_path='train', block_size=512):
        assert os.path.isfile(file_path)
        model_type = model_type.split("-")[0]
        directory, filename = os.path.split(file_path)
        cached_features_file = os.path.join(directory, 'cached_doimerged_' + str(block_size) + '_' + filename + ".npy")

        if os.path.exists(cached_features_file):
            logger.info("Loading features from cached file %s", cached_features_file)
            self.examples = np.load(cached_features_file)
        else:
            logger.info("Creating features from dataset file at %s", directory)

            dois = ["Electronics/Computers & Accessories/Laptops", "Restaurants"]
            
            logger.info("Domain of Interests (DOIs) %s", str(dois))
            
            domain_corpus = defaultdict(lambda: defaultdict(lambda : defaultdict(list)))

            with open(file_path, encoding="utf-8") as f:
                tag_on = True
                for line in f:
                    text = line.strip()
                    if len(text) == 0:
                        tag_on = True
                    elif tag_on:
                        tag_on = False
                        segs = text.split()
                        asin = segs[0]
                        rating = segs[-1]
                        domain = "/".join(" ".join(segs[1:-1]).split("/")[:3])
                    else:
                        if domain not in dois:
                            domain_corpus[domain][rating][asin].append(text)
                                            
            logger.info("Total number of %d domains", len(domain_corpus))
            
            if "train" in file_path:
                domain_to_id = {"[DOI]": 0}
                for ix, domain in enumerate(domain_corpus):
                    if domain not in dois:
                        domain_to_id[domain]=len(domain_to_id)
                with open(os.path.join(directory, "doi_domain.json"), "w") as fw:            
                    json.dump(domain_to_id, fw)
            else:
                with open(os.path.join(directory, "doi_domain.json")) as f:            
                    domain_to_id = json.load(f)

            block = [-100] * block_size
            self.examples = []

            for domain in domain_corpus:
                logger.info("Processing domain %s", domain)

                for rating in domain_corpus[domain]:
                    logger.info("| rating %s", rating)
                    # always use a new buffer for a new domain and rating.
                    buffer = deque()
                    for asin in domain_corpus[domain][rating]:
                        for text in domain_corpus[domain][rating][asin]:

                            tokens = tokenizer.tokenize(text)
                            buffer.extend(tokens)

                            # need to ensure enough text for short and long before making any example.
                            while len(buffer) >= block_size:
                                for ix in range(block_size):
                                    block[ix] = buffer.popleft()
                                input_ids = tokenizer.convert_tokens_to_ids(block)

                                if domain in dois:
                                    domain_seg = [domain_to_id["[DOI]"]]
                                else:
                                    domain_seg = [domain_to_id[domain]]
                                input_ids = domain_seg + tokenizer.build_inputs_with_special_tokens(input_ids)

                                self.examples.append(np.array([input_ids], dtype = np.uint16))
                                if len(self.examples) % 5000 == 0:
                                    logger.info("Processed %i examples", len(self.examples))                
                                    logger.info("one example is like %s", " ".join(tokenizer.convert_ids_to_tokens(input_ids)))
                        # clean up the memory.
                        domain_corpus[domain][rating][asin] = []

            self.examples = np.concatenate(self.examples)
            logger.info("Saving features into cached file %s", cached_features_file)
            np.save(cached_features_file, self.examples)


class LaptopTSDataset(TextDataset):
    def __init__(self, model_type, masker, tokenizer, file_path='train', block_size=512):
        assert os.path.isfile(file_path)
        model_type = model_type.split("-")[0]
        directory, filename = os.path.split(file_path)
        cached_features_file = os.path.join(directory, 'cached_doimerged_laptop_' + str(block_size) + '_' + filename + ".npy")

        if os.path.exists(cached_features_file):
            logger.info("Loading features from cached file %s", cached_features_file)
            self.examples = np.load(cached_features_file)
        else:
            raise Exception
            

class RestTSDataset(TextDataset):
    def __init__(self, model_type, masker, tokenizer, file_path='train', block_size=512):
        assert os.path.isfile(file_path)
        model_type = model_type.split("-")[0]
        directory, filename = os.path.split(file_path)
        cached_features_file = os.path.join(directory, 'cached_doimerged_restaurant_' + str(block_size) + '_' + filename + ".npy")

        if os.path.exists(cached_features_file):
            logger.info("Loading features from cached file %s", cached_features_file)
            self.examples = np.load(cached_features_file)
        else:
            raise Exception


class LaptopDomainDataset(TextDataset):
    def __init__(self, model_type, masker, tokenizer, file_path='train', block_size=512):
        assert os.path.isfile(file_path)
        model_type = model_type.split("-")[0]
        directory, filename = os.path.split(file_path)
        cached_features_file = os.path.join(directory, 'cached_laptop_' + str(block_size) + '_' + filename + ".npy")

        if os.path.exists(cached_features_file):
            logger.info("Loading features from cached file %s", cached_features_file)
            self.examples = np.load(cached_features_file)
        else:
            logger.info("Creating features from dataset file at %s", directory)

            dois = ["Electronics/Computers & Accessories/Laptops"]

            logger.info("Domain of Interests (DOIs) %s", str(dois))
            
            domain_corpus = defaultdict(lambda: defaultdict(lambda : defaultdict(list)))

            with open(file_path, encoding="utf-8") as f:
                tag_on = True
                for line in f:
                    text = line.strip()
                    if len(text) == 0:
                        tag_on = True
                    elif tag_on:
                        tag_on = False
                        segs = text.split()
                        asin = segs[0]
                        rating = segs[-1]
                        domain = "/".join(" ".join(segs[1:-1]).split("/")[:3])
                    else:
                        if domain in dois:
                            domain_corpus[domain][rating][asin].append(text)
            
            logger.info("Total number of %d domains", len(domain_corpus))
            
            with open(os.path.join(directory, "doi_domain.json")) as f:            
                domain_to_id = json.load(f)

            block = [-100] * block_size
            self.examples = []

            for domain in domain_corpus:
                logger.info("Processing domain %s", domain)

                for rating in domain_corpus[domain]:
                    logger.info("| rating %s", rating)
                    # always use a new buffer for a new domain and rating.
                    buffer = deque()
                    for asin in domain_corpus[domain][rating]:
                        for text in domain_corpus[domain][rating][asin]:

                            tokens = tokenizer.tokenize(text)
                            buffer.extend(tokens)

                            # need to ensure enough text for short and long before making any example.
                            while len(buffer) >= block_size:
                                for ix in range(block_size):
                                    block[ix] = buffer.popleft()
                                input_ids = tokenizer.convert_tokens_to_ids(block)

                                if domain in dois:
                                    domain_seg = [domain_to_id["[DOI]"]]
                                else:
                                    raise ValueError("domain %s is not in DOI", domain)
                                    
                                input_ids = domain_seg + tokenizer.build_inputs_with_special_tokens(input_ids)

                                self.examples.append(np.array([input_ids], dtype = np.uint16))
                                if len(self.examples) % 5000 == 0:
                                    logger.info("Processed %i examples", len(self.examples))                
                                    logger.info("one example is like %s", " ".join(tokenizer.convert_ids_to_tokens(input_ids)))
                        # clean up the memory.
                        domain_corpus[domain][rating][asin] = []

            self.examples = np.concatenate(self.examples)
            logger.info("Saving features into cached file %s", cached_features_file)
            np.save(cached_features_file, self.examples)


class RestDomainDataset(TextDataset):
    def __init__(self, model_type, masker, tokenizer, file_path='train', block_size=512):
        assert os.path.isfile(file_path)
        model_type = model_type.split("-")[0]
        directory, filename = os.path.split(file_path)
        cached_features_file = os.path.join(directory, 'cached_restaurant_' + str(block_size) + '_' + filename + ".npy")

        if os.path.exists(cached_features_file):
            logger.info("Loading features from cached file %s", cached_features_file)
            self.examples = np.load(cached_features_file)
        else:
            logger.info("Creating features from dataset file at %s", directory)

            dois = ["Restaurants"] # ["Electronics/Computers & Accessories/Laptops"]

            logger.info("Domain of Interests (DOIs) %s", str(dois))
            
            domain_corpus = defaultdict(lambda: defaultdict(lambda : defaultdict(list)))

            with open(file_path, encoding="utf-8") as f:
                tag_on = True
                for line in f:
                    text = line.strip()
                    if len(text) == 0:
                        tag_on = True
                    elif tag_on:
                        tag_on = False
                        segs = text.split()
                        asin = segs[0]
                        rating = segs[-1]
                        domain = "/".join(" ".join(segs[1:-1]).split("/")[:3])
                    else:
                        if domain in dois:
                            domain_corpus[domain][rating][asin].append(text)
            
            logger.info("Total number of %d domains", len(domain_corpus))
            
            with open(os.path.join(directory, "doi_domain.json")) as f:            
                domain_to_id = json.load(f)

            block = [-100] * block_size
            self.examples = []

            for domain in domain_corpus:
                logger.info("Processing domain %s", domain)

                for rating in domain_corpus[domain]:
                    logger.info("| rating %s", rating)
                    # always use a new buffer for a new domain and rating.
                    buffer = deque()
                    for asin in domain_corpus[domain][rating]:
                        for text in domain_corpus[domain][rating][asin]:

                            tokens = tokenizer.tokenize(text)
                            buffer.extend(tokens)

                            # need to ensure enough text for short and long before making any example.
                            while len(buffer) >= block_size:
                                for ix in range(block_size):
                                    block[ix] = buffer.popleft()
                                input_ids = tokenizer.convert_tokens_to_ids(block)

                                if domain in dois:
                                    domain_seg = [domain_to_id["[DOI]"]]
                                else:
                                    raise ValueError("domain %s is not in DOI", domain)
                                    
                                input_ids = domain_seg + tokenizer.build_inputs_with_special_tokens(input_ids)

                                self.examples.append(np.array([input_ids], dtype = np.uint16))
                                if len(self.examples) % 5000 == 0:
                                    logger.info("Processed %i examples", len(self.examples))                
                                    logger.info("one example is like %s", " ".join(tokenizer.convert_ids_to_tokens(input_ids)))
                        # clean up the memory.
                        domain_corpus[domain][rating][asin] = []

            self.examples = np.concatenate(self.examples)
            logger.info("Saving features into cached file %s", cached_features_file)
            np.save(cached_features_file, self.examples)


class LRDataset(TextDataset):
    def __init__(self, model_type, masker, tokenizer, file_path='train', block_size=512):
        assert os.path.isfile(file_path)
        model_type = model_type.split("-")[0]
        directory, filename = os.path.split(file_path)
        cached_features_file = os.path.join(directory, 'cached_lr_' + str(block_size) + '_' + filename + ".npy")

        if os.path.exists(cached_features_file):
            logger.info("Loading features from cached file %s", cached_features_file)
            self.examples = np.load(cached_features_file)
        else:
            logger.info("Creating features from dataset file at %s", directory)

            dois = ["Electronics/Computers & Accessories/Laptops", "Restaurants"]

            logger.info("Domain of Interests (DOIs) %s", str(dois))
            
            domain_corpus = defaultdict(lambda: defaultdict(lambda : defaultdict(list)))

            with open(file_path, encoding="utf-8") as f:
                tag_on = True
                for line in f:
                    text = line.strip()
                    if len(text) == 0:
                        tag_on = True
                    elif tag_on:
                        tag_on = False
                        segs = text.split()
                        asin = segs[0]
                        rating = segs[-1]
                        domain = "/".join(" ".join(segs[1:-1]).split("/")[:3])
                    else:
                        if domain in dois:
                            domain_corpus[domain][rating][asin].append(text)
            
            logger.info("Total number of %d domains", len(domain_corpus))
            
            with open(os.path.join(directory, "doi_domain.json")) as f:            
                domain_to_id = json.load(f)

            block = [-100] * block_size
            self.examples = []

            for domain in domain_corpus:
                logger.info("Processing domain %s", domain)

                for rating in domain_corpus[domain]:
                    logger.info("| rating %s", rating)
                    # always use a new buffer for a new domain and rating.
                    buffer = deque()
                    for asin in domain_corpus[domain][rating]:
                        for text in domain_corpus[domain][rating][asin]:

                            tokens = tokenizer.tokenize(text)
                            buffer.extend(tokens)

                            # need to ensure enough text for short and long before making any example.
                            while len(buffer) >= block_size:
                                for ix in range(block_size):
                                    block[ix] = buffer.popleft()
                                input_ids = tokenizer.convert_tokens_to_ids(block)

                                if domain in dois:
                                    domain_seg = [domain_to_id["[DOI]"]]
                                else:
                                    raise ValueError("domain %s is not in DOI", domain)
                                    
                                input_ids = domain_seg + tokenizer.build_inputs_with_special_tokens(input_ids)

                                self.examples.append(np.array([input_ids], dtype = np.uint16))
                                if len(self.examples) % 5000 == 0:
                                    logger.info("Processed %i examples", len(self.examples))                
                                    logger.info("one example is like %s", " ".join(tokenizer.convert_ids_to_tokens(input_ids)))
                        # clean up the memory.
                        domain_corpus[domain][rating][asin] = []

            self.examples = np.concatenate(self.examples)
            logger.info("Saving features into cached file %s", cached_features_file)
            np.save(cached_features_file, self.examples)

        
class DiverseTagEmbDataset(TextDataset):
    """
        This class read the text file with tags and encode a tag with an embedding index.
    """
    def __init__(self, model_type, masker, tokenizer, file_path='train', block_size=512):

        assert os.path.isfile(file_path)
        model_type = model_type.split("-")[0]
        directory, filename = os.path.split(file_path)
        cached_features_file = os.path.join(directory, 'cached_diversetagemb_' + str(block_size) + '_' + filename + ".npy")

        if os.path.exists(cached_features_file):
            logger.info("Loading features from cached file %s", cached_features_file)
            self.examples = np.load(cached_features_file)
        else:
            logger.info("Creating features from dataset file at %s", directory)
            
            domain_corpus = defaultdict(lambda: defaultdict(lambda : defaultdict(list)))
            with open(file_path, encoding="utf-8") as f:
                tag_on = True
                for line in f:
                    text = line.strip()
                    if len(text) == 0:
                        tag_on = True
                    elif tag_on:
                        tag_on = False
                        segs = text.split()
                        asin = segs[0]
                        rating = segs[-1]
                        domain = "/".join(" ".join(segs[1:-1]).split("/")[:3])
                    else:
                        if len(domain_corpus[domain][rating]) < 50:
                            domain_corpus[domain][rating][asin].append(text)
            
            logger.info("Total number of %d domains", len(domain_corpus))
            if "train" in file_path:
                domain_to_id = {"[GENERAL]": 0, "[OTHER]": 1}
                for ix, domain in enumerate(domain_corpus):
                    domain_to_id[domain]=len(domain_to_id)
                with open(os.path.join(directory, "diverse_domain.json"), "w") as fw:            
                    json.dump(domain_to_id, fw)
            else:
                with open(os.path.join(directory, "diverse_domain.json")) as f:            
                    domain_to_id = json.load(f)

            block = [-100] * block_size
            self.examples = []

            for domain in domain_corpus:
                logger.info("Processing domain %s", domain)

                for rating in domain_corpus[domain]:
                    logger.info("| rating %s", rating)
                    # always use a new buffer for a new domain and rating.
                    buffer = deque()
                    for asin in domain_corpus[domain][rating]:
                        for text in domain_corpus[domain][rating][asin]:

                            tokens = tokenizer.tokenize(text)
                            buffer.extend(tokens)

                            # need to ensure enough text for short and long before making any example.
                            while len(buffer) >= block_size:
                                for ix in range(block_size):
                                    block[ix] = buffer.popleft()
                                input_ids = tokenizer.convert_tokens_to_ids(block)

                                if domain in domain_to_id:
                                    domain_seg = [domain_to_id[domain]]
                                else:
                                    domain_seg = [domain_to_id["[OTHER]"]]
                                input_ids = domain_seg + tokenizer.build_inputs_with_special_tokens(input_ids)

                                self.examples.append(np.array([input_ids], dtype = np.uint16))
                                if len(self.examples) % 5000 == 0:
                                    logger.info("Processed %i examples", len(self.examples))                
                                    logger.info("one example is like %s", " ".join(tokenizer.convert_ids_to_tokens(input_ids)))
                        # clean up the memory.
                        domain_corpus[domain][rating][asin] = []

            self.examples = np.concatenate(self.examples)
            logger.info("Saving features into cached file %s", cached_features_file)
            np.save(cached_features_file, self.examples)

            
class LRTagEmbDataset(TextDataset):
    """
        This class read the text file with tags and encode a tag with an embedding index.
    """
    def __init__(self, model_type, masker, tokenizer, file_path='train', block_size=512):

        assert os.path.isfile(file_path)
        model_type = model_type.split("-")[0]
        directory, filename = os.path.split(file_path)
        cached_features_file = os.path.join(directory, 'cached_lrtagemb_' + str(block_size) + '_' + filename + ".npy")

        if os.path.exists(cached_features_file):
            logger.info("Loading features from cached file %s", cached_features_file)
            self.examples = np.load(cached_features_file)
        else:
            logger.info("Creating features from dataset file at %s", directory)
            
            domain_corpus = defaultdict(lambda: defaultdict(lambda : defaultdict(list)))
            with open(file_path, encoding="utf-8") as f:
                tag_on = True
                for line in f:
                    text = line.strip()
                    if len(text) == 0:
                        tag_on = True
                    elif tag_on:
                        tag_on = False
                        segs = text.split()
                        asin = segs[0]
                        rating = segs[-1]
                        domain = "/".join(" ".join(segs[1:-1]).split("/")[:3])
                    else:
                        if len(domain_corpus[domain][rating]) < 5000:
                            domain_corpus[domain][rating][asin].append(text)
            
            logger.info("Total number of %d domains", len(domain_corpus))
            if "train" in file_path:
                domain_to_id = {"[GENERAL]": 0, "[OTHER]": 1}
                for ix, domain in enumerate(domain_corpus):
                    domain_to_id[domain]=len(domain_to_id)
                with open(os.path.join(directory, "diverse_domain.json"), "w") as fw:            
                    json.dump(domain_to_id, fw)
            else:
                with open(os.path.join(directory, "diverse_domain.json")) as f:            
                    domain_to_id = json.load(f)

            block = [-100] * block_size
            self.examples = []

            for domain in ["Electronics/Computers & Accessories/Laptops", "Restaurants"]:
                logger.info("Processing domain %s", domain)

                for rating in domain_corpus[domain]:
                    logger.info("| rating %s", rating)
                    # always use a new buffer for a new domain and rating.
                    buffer = deque()
                    for asin in domain_corpus[domain][rating]:
                        for text in domain_corpus[domain][rating][asin]:

                            tokens = tokenizer.tokenize(text)
                            buffer.extend(tokens)

                            # need to ensure enough text for short and long before making any example.
                            while len(buffer) >= block_size:
                                for ix in range(block_size):
                                    block[ix] = buffer.popleft()
                                input_ids = tokenizer.convert_tokens_to_ids(block)

                                if domain in domain_to_id:
                                    domain_seg = [domain_to_id[domain]]
                                else:
                                    domain_seg = [domain_to_id["[OTHER]"]]
                                input_ids = domain_seg + tokenizer.build_inputs_with_special_tokens(input_ids)

                                self.examples.append(np.array([input_ids], dtype = np.uint16))
                                if len(self.examples) % 5000 == 0:
                                    logger.info("Processed %i examples", len(self.examples))                
                                    logger.info("one example is like %s", " ".join(tokenizer.convert_ids_to_tokens(input_ids)))
                        # clean up the memory.
                        domain_corpus[domain][rating][asin] = []

            self.examples = np.concatenate(self.examples)
            logger.info("Saving features into cached file %s", cached_features_file)
            np.save(cached_features_file, self.examples)


class SkipTagDataset(TextDataset):
    """
    This class is used for dataset with mixed domains.
    """
    def __init__(self, model_type, masker, tokenizer, file_path='train', block_size=512):
        assert os.path.isfile(file_path)
        model_type = model_type.split("-")[0]
        directory, filename = os.path.split(file_path)
        cached_features_file = os.path.join(directory, 'cached_skiptag_' + str(block_size) + '_' + filename + ".npy")

        if os.path.exists(cached_features_file):
            logger.info("Loading features from cached file %s", cached_features_file)
            self.examples = np.load(cached_features_file)
        else:
            logger.info("Creating features from dataset file at %s", directory)

            self.examples = []
            with open(file_path, encoding="utf-8") as f:
                buffer = []
                tag_on = True
                for line in f:
                    text = line.strip()
                    if len(text) == 0:
                        tag_on = True
                    elif tag_on:
                        tag_on = False
                        if len(self.examples) % 5000 == 0:
                            logger.info("Skip tag %s", text)
                    else:
                        tokens = tokenizer.tokenize(text)
                        buffer.extend(tokens)
                        while len(buffer) >= block_size:
                            self.examples.append(
                                np.array(
                                    [tokenizer.build_inputs_with_special_tokens(tokenizer.convert_tokens_to_ids(buffer[:block_size]))], 
                                    dtype = np.uint16))
                            if len(self.examples) % 5000 == 0:
                                logger.info("Processed %i examples", len(self.examples))
                            buffer = buffer[block_size:]
            self.examples = np.concatenate(self.examples)
            logger.info("Saving features into cached file %s", cached_features_file)
            np.save(cached_features_file, self.examples)

    
def load_and_cache_examples(dataset_cls, args, masker, tokenizer, evaluate=False):
    dataset = dataset_cls(args.model_type, masker, tokenizer, file_path=args.eval_data_file if evaluate else args.train_data_file, block_size=args.block_size)
    return dataset
